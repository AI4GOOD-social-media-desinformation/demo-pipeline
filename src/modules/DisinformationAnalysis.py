from google import genai
from src.eventbus.InMemoryEventBus import InMemoryEventBus

from firebase_admin import firestore
import os


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class DisinformationAnalysis:
    """
    Module for analyzing claims and context for disinformation, fake news, and manipulation.
    Processes extracted claims and video context to generate risk assessment and top evidences.
    """

    def __init__(self, project_id: str = "gen-lang-client-0915299548", database: str = "ai4good", eventbus: InMemoryEventBus = None):
        """
        Initialize DisinformationAnalysis with Firestore credentials.
        
        Args:
            project_id: GCP project ID for Firestore
            database: Firestore database name
            eventbus: InMemoryEventBus instance for event publishing
        """
        self.db = firestore.Client(project=project_id, database=database)
        self.client = genai.Client(api_key=GOOGLE_API_KEY)
        self.model = "gemini-2.5-flash"
        self.eventbus = eventbus

    def set_eventbus(self, eventbus: InMemoryEventBus):
        """
        Set the event bus for publishing events.
        
        Args:
            eventbus: InMemoryEventBus instance
        """
        self.eventbus = eventbus

    def analyze_disinformation(self, claim: str, context: str) -> str:
        """
        Analyze claim/context and return a compact, line-based summary that is easy to split.
        """
        analysis_prompt = f"""
        Você é um especialista em desinformação. Analise a afirmação e o contexto e responda uma análise em português brasileiro que:
        1. Indique o nível de risco (ALTO, MÉDIO ou BAIXO)
        2. Apresente as TOP 2 evidências que suportam essa conclusão
        
        A análise deve considerar:
        - Afirmações falsas ou enganosas
        - Falta de fontes confiáveis ou verificação
        - Manipulação emocional ou sensacionalismo
        - Informações fora de contexto
        - Teorias conspiratórias não comprovadas
        - Indicadores de deepfakes ou mídia manipulada
        
        O retorno deve ser EXATAMENTE neste formato em português (sem texto extra, sem JSON):

        Risco: <texto curto>
        Evidencia 1: <texto curto>
        Evidencia 2: <texto curto>

        Se alguma evidência não existir, use "N/A" no lugar do texto. Mantenha as evidências
        objetivas e com no máximo 500 caracteres cada.

        Afirmação: {claim}
        Contexto: {context}
        """

        response = self.client.models.generate_content(
            model=self.model,
            contents=[analysis_prompt]
        )

        try:
            return response.text.strip()
        except Exception as e:
            print(f"Error generating analysis: {e}")
            return "Risco: N/A\nEvidencia 1: N/A\nEvidencia 2: N/A"

    def _extract_messages(self, raw_text: str) -> list[str]:
        """Parse the model response into individual short messages for DM sending."""
        messages: list[str] = []

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        risk_line = next((l for l in lines if l.lower().startswith("risco:")), None)
        if risk_line:
            messages.append(risk_line)

        evidence_lines = [l for l in lines if l.lower().startswith("evidencia")]
        # Keep first two evidence lines to avoid DM spam
        for ev in evidence_lines[:2]:
            messages.append(ev)

        # Fallback to whole text if parsing failed
        if not messages and raw_text:
            messages.append(raw_text[:1000])

        return messages

    def sanity_check_event_data(self, data: dict) -> None:
        """
        Ensure required fields are present in event data.
        
        Args:
            data: Event data dictionary
            
        Raises:
            ValueError: If any required field is missing
        """
        required_fields = ["id", "data"]
        required_fields_data = ["claim", "context"]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field in event data: {field}")
            
        for field in required_fields_data:
            if field not in data["data"]:
                raise ValueError(f"Missing required field in event data['data']: {field}")

    def run(self, event_data: dict) -> dict:
        """
        Main method: Analyze claim and context for disinformation and save to Firestore.
        
        Args:
            event_data: Event data containing:
                - id: Document ID
                - data: Dictionary with claim, context, and other fields from claim extraction
                
        Returns:
            Dictionary containing:
                - id: Firestore document ID
                - message: Analysis message in Portuguese (Brazil)
        """
        try:
            self.sanity_check_event_data(event_data)
            
            claim = event_data["data"].get("claim", "")
            context = event_data["data"].get("context", "")
            
            # Step 1: Analyze disinformation
            raw_message = self.analyze_disinformation(claim, context)
            messages = self._extract_messages(raw_message)

            # Step 2: Add messages to event data
            event_data["data"]["analysisMessage"] = "\n".join(messages)
            event_data["data"]["messages"] = messages
            
            # Step 3: Update Firestore document with analysis message
            try:
                self.db.collection('requests').document(event_data["id"]).update({
                    "analysisMessage": event_data["data"]["analysisMessage"],
                    "messages": messages,
                })
            except Exception as e:
                print(f"Error updating Firestore with ID: {event_data['id']}, error: {e}")
                self.eventbus.publish("disinformation_analysis.failed", {
                    "id": event_data["id"],
                    "error": "Firestore update error"
                })
                return
            
            # Step 4: Publish success event
            self.eventbus.publish("disinformation_analysis.completed", {
                "id": event_data["id"],
                "data": event_data["data"]
            })
            
            return event_data["data"]
            
        except ValueError as e:
            print(f"Validation error: {e}")
            self.eventbus.publish("disinformation_analysis.failed", {
                "id": event_data.get("id", "unknown"),
                "error": str(e)
            })
            return None

    def on_disinformation_analysis_completed(self, event_data):
        """Handle successful disinformation analysis completion."""
        print(f"Análise de desinformação concluída para ID: {event_data['id']}")
        print(f"Mensagem: {event_data['data'].get('message', 'N/A')}")

    def on_disinformation_analysis_failed(self, event_data):
        """Handle disinformation analysis failure."""
        print(f"Análise de desinformação falhou para ID: {event_data['id']}, Erro: {event_data['error']}")
