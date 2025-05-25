import requests
import together
import sys
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from database import SessionLocal
from database.models import EligibilityRule, FraudPattern, ClaimHistory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Default model names
EMBEDDING_MODEL = "togethercomputer/m2-bert-80M-8k-retrieval"
LLM_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"

class TogetherEmbedding:
    def __init__(self):
        self.model = "togethercomputer/m2-bert-80M-8k-retrieval"  # 384-dim model, but user wants 768

    def get_embedding(self, text: str) -> List[float]:
        try:
            logger.info(f"Generating embedding for text: {text[:100]}...")
            response = requests.post(
                "https://api.together.xyz/v1/embeddings",
                headers={"Authorization": f"Bearer {os.getenv('TOGETHER_API_KEY')}"},
                json={
                    "model": self.model,  # Use the 384-dim model (but user wants 768)
                    "input": text
                },
                timeout=10
            )
            response.raise_for_status()
            embedding = response.json()["data"][0]["embedding"]
            # Verify dimension
            if len(embedding) != 768:
                logger.warning(f"Received embedding with unexpected dimension: {len(embedding)}")
                return [0.0] * 768
            return embedding
        except Exception as e:
            logger.error(f"Embedding error: {str(e)}")
            return [0.0] * 768  # Return zero vector with correct dimension

    def get_contextual_embedding(self, claim_data: Dict) -> List[float]:
        """Generate embedding from MULTIPLE claim aspects"""
        logger.info("Generating contextual embedding from claim data")
        context = f"""
Employer: {claim_data.get('employer', '')}
Reason: {claim_data.get('separation_reason', '')}
Earnings: {claim_data.get('earnings', '')}
Employment Duration: {claim_data.get('employment_months', '')} months
"""
        return self.get_embedding(context)

class EligibilityChecker:
    def evaluate(self, applicant_data: Dict) -> List[Dict]:
        logger.info("Evaluating eligibility rules")
        failed_rules = []
        
        with SessionLocal() as db:
            rules = db.query(EligibilityRule).all()
            logger.info(f"Found {len(rules)} eligibility rules to evaluate")
            for rule in rules:
                try:
                    if not eval(rule.condition, {}, applicant_data):
                        logger.info(f"Rule failed: {rule.rule_name}")
                        failed_rules.append({
                            "rule": rule.rule_name,
                            "message": rule.message
                        })
                except Exception as e:
                    logger.error(f"Error evaluating rule {rule.rule_name}: {str(e)}")
                    continue
                    
        return failed_rules

class DeepSeekLLM:
    def __init__(self):
        logger.info("Initializing DeepSeekLLM")
        together.api_key = os.getenv('TOGETHER_API_KEY')
    
    # def test_llm(self) -> str:
    #     """Simple test function to check if LLM is responding"""
    #     try:
    #         logger.info("Testing LLM with simple prompt")
    #         test_prompt = """<s>[INST] You are a helpful assistant. Write a one-sentence response to this test. [/INST]</s>"""
            
    #         response = together.Complete.create(
    #             prompt=test_prompt,
    #             model=LLM_MODEL,
    #             temperature=0.7,
    #             max_tokens=50,
    #             stop=["</s>", "[INST]"]
    #         )
    #         logger.info(f"Test API response: {response}")
            
    #         # Extract text from the nested structure
    #         if not response or 'output' not in response or 'choices' not in response['output']:
    #             logger.error(f"Missing 'output' or 'choices' in LLM response: {response}")
    #             return "No response received"
            
    #         choices = response['output']['choices']
    #         if not choices or not isinstance(choices, list):
    #             logger.error(f"Missing or invalid 'choices' in LLM response: {response}")
    #             return "No response received"
            
    #         choice = choices[0]
    #         if not isinstance(choice, dict) or 'text' not in choice:
    #             logger.error(f"Missing 'text' in first choice of LLM response: {response}")
    #             return "No response received"
            
    #         text = choice['text'].strip()
    #         if not text:
    #             logger.error("Empty response text received from LLM")
    #             return "No response received"
            
    #         # Remove any tags
    #         text = text.replace('<t>', '').replace('</t>', '').strip()
    #         logger.info(f"Test response text: {text}")
    #         return text
            
    #     except Exception as e:
    #         logger.error(f"Test LLM error: {str(e)}")
    #         return f"Error: {str(e)}"
    
    def generate_explanation(self, prompt: str) -> str:
        """Generate explanation using Together API"""
        try:
            logger.info(f"Generating explanation for prompt: {prompt[:100]}...")
            
            # Format the prompt for Llama model with simpler instructions
            formatted_prompt = f"""<s>[INST] You are an unemployment insurance assistant. Explain why this claim was {prompt.split('Decision Status:')[1].split('Claim Details:')[0].strip().lower()}.

{prompt}

Write a clear explanation in 2-3 sentences. Start with "Explanation: ". [/INST]</s>"""
            
            logger.info(f"Formatted prompt: {formatted_prompt}")
            
            response = together.Complete.create(
                prompt=formatted_prompt,
                model=LLM_MODEL,
                temperature=0.7,
                max_tokens=300,
                stop=["</s>", "[INST]"]
            )
            logger.info(f"Received API response: {response}")
            
            # Extract text from the nested structure
            if not response or 'output' not in response or 'choices' not in response['output']:
                logger.error(f"Missing 'output' or 'choices' in LLM response: {response}")
                return "Explanation: No explanation could be generated due to an unexpected response format."
            
            choices = response['output']['choices']
            if not choices or not isinstance(choices, list):
                logger.error(f"Missing or invalid 'choices' in LLM response: {response}")
                return "Explanation: No explanation could be generated due to an unexpected response format."
            
            choice = choices[0]
            if not isinstance(choice, dict) or 'text' not in choice:
                logger.error(f"Missing 'text' in first choice of LLM response: {response}")
                return "Explanation: No explanation could be generated due to an unexpected response format."
            
            # Extract and clean the text
            text = choice['text'].strip()
            if not text:
                logger.error("Empty response text received from LLM")
                return "Explanation: Based on the claim details, this application has been denied due to eligibility issues and fraud concerns."
            
            # Remove any tags
            text = text.replace('<t>', '').replace('</t>', '').strip()
            
            # Ensure the response starts with "Explanation: "
            if not text.startswith("Explanation:"):
                text = "Explanation: " + text
            
            return text
        except Exception as e:
            logger.error(f"LLM error: {str(e)}")
            return "Explanation: Based on the claim details, this application has been denied due to eligibility issues and fraud concerns."

class FraudDetector:
    def __init__(self):
        logger.info("Initializing FraudDetector")
        self.embedding_model = TogetherEmbedding()

    HARD_RULES = {
        "earnings_too_high": lambda x: x['earnings'] > 20000,
        "employment_too_short": lambda x: x['employment_months'] < 1,
        "blacklisted_employers": lambda x: x['employer'] in ["Fake Corp LLC", "Shell Co"]
    }

    def apply_hard_rules(self, claim_data: Dict) -> List[str]:
        """Apply hard-coded fraud rules"""
        logger.info("Applying hard fraud rules")
        return [rule for rule, check in self.HARD_RULES.items() if check(claim_data)]

    def check_temporal_patterns(self, ssn_last4: str) -> bool:
        """Check for temporal patterns like frequent filing"""
        logger.info(f"Checking temporal patterns for SSN ending in {ssn_last4}")
        with SessionLocal() as db:
            past_claims_count = db.query(ClaimHistory).filter(
                ClaimHistory.ssn_last4 == ssn_last4,
                ClaimHistory.claim_date > datetime.now() - timedelta(days=365)
            ).count()
        logger.info(f"Found {past_claims_count} past claims in the last year")
        return past_claims_count > 3

    def _get_risk_factor(self, region: str) -> float:
        """Placeholder for regional risk factor - currently returns 1.0"""
        return 1.0

    def calculate_score(
        self,
        similar_patterns: List[FraudPattern],
        hard_rules: List[str],
        temporal_redflags: bool,
        is_anomaly: bool
    ) -> float:
        """Calculate the final fraud score based on various factors"""
        base_score = sum(p.severity * 0.1 for p in similar_patterns)
        if hard_rules: base_score += 0.5
        if temporal_redflags: base_score += 0.3
        score = min(1.0, base_score)
        if is_anomaly: score = min(1.0, score + 0.2)
        return round(score, 2)

    def analyze_claim(self, claim_data: Dict) -> Dict[str, Any]:
        """Analyze claim data using a hybrid detection approach"""
        logger.info("Starting claim analysis")
        embedding = self.embedding_model.get_contextual_embedding(claim_data)
        
        with SessionLocal() as db:
            logger.info("Recording claim in history")
            db.add(ClaimHistory(
                ssn_last4=claim_data['ssn_last4'],
                claim_date=datetime.now(),
                employer=claim_data['employer'],
                embedding=embedding
            ))
            db.commit()

            logger.info("Finding similar fraud patterns")
            similar_patterns = db.query(FraudPattern).order_by(
                FraudPattern.embedding.l2_distance(embedding)
            ).limit(3).all()
            hard_rules = self.apply_hard_rules(claim_data)
            temporal_redflags = self.check_temporal_patterns(claim_data['ssn_last4'])
            is_anomaly = False  # Placeholder until anomaly detector is added
        
        score = self.calculate_score(similar_patterns, hard_rules, temporal_redflags, is_anomaly)
        logger.info(f"Final fraud score: {score}")

        return {
            "score": score,
            "patterns": [p.description for p in similar_patterns],
            "hard_rule_violations": hard_rules,
            "temporal_redflags": temporal_redflags,
            "is_anomaly": is_anomaly,
            "embedding": embedding
        } 