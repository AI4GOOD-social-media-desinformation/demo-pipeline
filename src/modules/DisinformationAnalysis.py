from typing import Any

from google import genai
from google.genai import types
from src.eventbus.InMemoryEventBus import InMemoryEventBus
from src.modules.NewsMatcher import NewsMatcher

from firebase_admin import firestore
import os
from time import time

from dataclasses import dataclass

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@dataclass
class Subclaim:
    claim_text: str
    evidence_types: list[str]
    query: list[str]
    verification_result: str | None = None
    justification: str | None = None


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class DisinformationAnalysis:
    """
    Module for analyzing claims and context for disinformation, fake news, and manipulation.
    Processes extracted claims and video context to generate risk assessment and top evidences.
    """

    def __init__(
            self,
            project_id: str = "gen-lang-client-0915299548",
            database: str = "ai4good",
            eventbus: InMemoryEventBus | None = None,
            n_subclaims: int = 2,
        ) -> None:
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

        self.n_subclaims = n_subclaims

    def set_eventbus(self, eventbus: InMemoryEventBus) -> None:
        """
        Set the event bus for publishing events.
        
        Args:
            eventbus: InMemoryEventBus instance
        """
        self.eventbus = eventbus

    def generate_subclaims(self, claim: str, n: int) -> list[Subclaim]:
        """
        Generate sub-claims for a given claim using the language model.
        
        Args:
            claim: The main claim text
            n: Number of sub-claims to generate
        
        Returns:
            List of Subclaim dataclass instances
        """

        prompt = f"""
            Você é um verificador de fatos.
            Afirmação: "{claim}"

            Gere {n} sub-afirmações testáveis que, se verificadas, provariam ou refutariam a afirmação original.
            Para cada sub-afirmação:
            - Especifique que tipo de evidência a confirmaria ou refutaria (dados, testemunho, documentação, registro temporal)
            - Forneça uma query de busca que recuperaria essa evidência com, no máximo, 3 termos de busca

            Somente retorne as perguntas em formato de lista com suas respectivas justificativas, sem qualquer texto adicional, com o seguinte formato:
            Sub-afirmação: [asserção específica]
            Tipo de evidência: [o que provaria/refutaria]
            Query de busca: [consulta para recuperar a evidência, ex: "<query 1>", "<query 2>"]

            Priorize sub-afirmações por:
            1. Observabilidade direta
            2. Menor número de passos inferenciais
            3. Disponibilidade de fontes primárias"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.2
            )
        )

        sub_claims: list[Subclaim] = []

        if not response.text:
            return sub_claims

        for item in response.text.split('\n\n'):
            lines = item.strip().split('\n')
            if len(lines) < 3:
                continue

            subclaim_text = lines[0].replace('Sub-afirmação: ', '').strip()
            evidence_type = lines[1].replace('Tipo de evidência: ', '').strip()
            query_text = lines[2].replace('Query de busca: ', '').strip()

            sub_claims.append(Subclaim(
                claim_text=subclaim_text,
                evidence_types=evidence_type.split(', '),
                query=[q.strip().strip('"') for q in query_text.split(',')]
            ))

        return sub_claims

    def retrieve_news(self, subclaim: Subclaim) -> list[dict[str, Any]]:
        """
        Retrieve news for a given sub-claim using search queries.
        
        Args:
            subclaim: Subclaim instance
        
        Returns:
            Retrieved news text
        """
        news_matcher = NewsMatcher()

        return news_matcher.run(subclaim.query)

    def check_subclaims(
            self,
            subclaims: list[Subclaim],
            news: list[dict[str, Any]],
            context: str,
            probVideoFake: float | None,
            probAudioFake: float | None
        ) -> None:
        """
        Verify each sub-claim against the provided context.
        Subclaims are updated in place with verification results.
        
        Args:
            subclaims: List of Subclaim instances
            news: List of news articles as dictionaries
            context: Video context text
            probVideoFake: Probability of video being fake
            probAudioFake: Probability of audio being fake
        """

        afirmations = [
            f"Afirmação {i}: \"{subclaim.claim_text}\""
            for i, subclaim in enumerate(subclaims, 1)
        ]

        news_titles = [
            f"Título da notícia relacionada a afirmação {i}: \"{article['title']}\""
            for i, _ in enumerate(subclaims, 1)
            for article in news
        ]

        prompt = f"""
        Você é um verificador de fatos e analista de contexto.
        Dado o seguinte contexto, notícias e afirmações, determine se a afirmação é suportada, refutada ou não pode ser verificada.
        Caso o a afirmação seja suportada

        Contexto: \"{context}\""""
        
        if probVideoFake is not None:
            prompt += f"\nProbabilidade do Vídeo ser Fake: {probVideoFake}"

        if probAudioFake is not None:
            prompt += f"\nProbabilidade do Áudio ser Fake: {probAudioFake}"

        prompt += f"""
        {'\n'.join(news_titles)}
        {'\n'.join(afirmations)}

        Responda para cada uma das afirmações apenas com uma das seguintes frases:
        - Suportada Além do Contexto
        - Potenciamente Suportada Além do Contexto
        - Suportada Apenas pelo Contexto
        - Suportada Fracamente pelo Contexto
        - Refutada pelo contexto
        - Refutada Além do Contexto
        - Não verificável
        no seguinte formato:
        Afirmação 1: [resultado]
        Justificativa: [breve explicação]
        Afirmação 2: [resultado]
        Justificativa: [breve explicação]
        ...
        """

        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.2
            )
        )
            
        if not response.text:
            for subclaim in subclaims:
                subclaim.verification_result = "Não verificável"
                subclaim.justification = "Erro ao gerar resposta"
            return
        
        # Parse the response and update subclaims
        lines = response.text.strip().split('\n')
        current_index = 0
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for "Afirmação N:" pattern
            if line.startswith('Afirmação'):
                # Extract verification result
                if ':' in line:
                    result = line.split(':', 1)[1].strip()
                    
                    # Look for justification on next line
                    justification = None
                    if i + 1 < len(lines) and lines[i + 1].strip().startswith('Justificativa:'):
                        justification = lines[i + 1].split(':', 1)[1].strip()
                        i += 1  # Skip the justification line in next iteration
                    
                    # Update the corresponding subclaim
                    if current_index < len(subclaims):
                        subclaims[current_index].verification_result = result
                        subclaims[current_index].justification = justification
                        current_index += 1
            
            i += 1

    def summarize_justifications(self, claim: str, subclaims: list[Subclaim], news: list[dict[str, Any]]) -> list[str]:
        """
        Summarize justifications for all sub-claims into concise messages to be sent via DM.

        Args:
            subclaims: List of Subclaim instances
            news: List of news articles as dictionaries
        
        Returns:
            List of summarized justification messages        
        """
        sub_claims_text = [
            f"Afirmação {i+1}: \"{subclaim.claim_text}\"\n"
            f"Veredito: {subclaim.verification_result or 'N/A'}\n"
            f"Justificativa: {subclaim.justification or 'N/A'}"
            for i, subclaim in enumerate(subclaims)
        ]


        prompt = f"""
        Você é um especialista em comunicação de desinformação.
        Dado um conjunto de sub-afirmações verificadas e notícias relacionadas, você deverá apresentar uma resumo conciso para o usuário final.
        Mantenha um tom neutro e cético e forneça apenas fatos e evidências relevantes, evitando julgamentos ou opiniões pessoais.

        \n\n{''.join(sub_claims_text)}\n\n

        Forma de Resposta:
        1. Indique o nível de risco de desingomarção (ALTO, MÉDIO ou BAIXO), em negrito
        2. Apresente as TOP 2 evidências que suportam essa conclusão

        O retorno deve ser EXATAMENTE neste formato em português (sem texto extra, sem JSON):

        Risco: <texto curto>
        Evidencia 1: <texto curto>
        Evidencia 2: <texto curto>


        """

        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.2
            )
        )

        if response.text:
            return [line.strip() for line in response.text.strip().splitlines() if line.strip()]

        return ["Houve um erro ao gerar o resumo das justificativas.", "Por favor, tente novamente mais tarde."]

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

        Se alguma evidência não existir, use "N/A" no lugar do texto. Mantenha as evidências com no máximo 600 caracteres cada.

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

    def sanity_check_event_data(self, data: dict[str, Any]) -> None:
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

    def run(self, event_data: dict[str, Any]) -> dict[str, Any]:
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
        logger.debug(f"Running DisinformationAnalysis with event data ID: {event_data.get('id', 'N/A')}")

        try:
            self.sanity_check_event_data(event_data)
            
            claim: str = event_data["data"].get("claim", "")
            context: str = event_data["data"].get("context", "")
            probVideoFake: float | None = event_data["data"].get("probVideoFake")
            probAudioFake: float | None = event_data["data"].get("probAudioFake")
            
            # # Step 1: Analyze disinformation
            # raw_message = self.analyze_disinformation(claim, context)
            # messages = self._extract_messages(raw_message)

            # Step 1: Generate subclaims

            logger.debug(f"Generating subclaims for claim: {claim[:50]}...")
            start = time()
            subclaims = self.generate_subclaims(claim, n=self.n_subclaims)
            logger.debug(f"Generated {len(subclaims)} subclaims in {time() - start:.2f} seconds.")

            # Step 2: Retrieve news for each subclaim

            logger.debug(f"Retrieving news for subclaims...")
            start = time()
            news: list[dict[str, Any]] = []
            for subclaim in subclaims:
                retrieved_news = self.retrieve_news(subclaim)
                news.extend(retrieved_news)
            
            logger.debug(f"Retrieved a total of {len(news)} news articles for subclaims in {time() - start:.2f} seconds.")

            # Step 3: Check subclaims against context
            logger.debug("Checking subclaims against context...")
            start = time()
            self.check_subclaims(subclaims, news, context, probVideoFake, probAudioFake)
            logger.debug(f"Checked subclaims in {time() - start:.2f} seconds.")

            # Step 4: Summarize justifications
            logger.debug("Summarizing justifications...")
            start = time()
            messages = self.summarize_justifications(claim, subclaims, news)
            logger.debug(f"Summarized justifications in {time() - start:.2f} seconds.")

            # DANIEL: A partir daqui não tinha certeza como continuar a integração com o Firestore e o eventbus
            # # Step 5: Add messages to event data
            event_data["data"]["analysisMessage"] = "\n".join(messages)
            event_data["data"]["messages"] = messages
            event_data["data"]["news"] = news

            # Step 6: Update Firestore document with analysis message
            try:
                self.db.collection('requests').document(event_data["id"]).update({
                    "analysisMessage": event_data["data"]["analysisMessage"],
                    "messages": messages,
                    "news": news,
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
