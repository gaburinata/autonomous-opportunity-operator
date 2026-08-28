"""Google ADK topology for Autonomous Opportunity Operator (configuration only)."""
from google.adk.agents import LlmAgent, SequentialAgent

from .adk_tools import (
    calculate_unit_economics,
    eligibility_capital_deadline_gate,
    authoritative_failure_memory_similarity_check as failure_memory_similarity_check,
    final_evidence_safety_adjudication,
)

MODEL = "gemini-3.5-flash"

discovery_agent = LlmAgent(name='discovery_agent', model=MODEL, instruction='You are the Discovery Agent.\n\nAnalyze only the authoritative source text and exact operator profile below.\n\nSOURCE:\n{source_text}\n\nOPERATOR PROFILE:\n{decision_profile_json}\n\nReturn a compact factual opportunity brief under 1800 characters.\nInclude only facts needed by later agents: opportunity purpose, deadline,\nprizes/upside, eligibility, required technology, required deliverables,\nimportant constraints, and unresolved facts. Do not invent facts.', include_contents='none', output_key='discovery_brief')
verification_agent = LlmAgent(name='primary_source_verification_agent', model=MODEL, instruction="You are the Primary Source Verification Agent.\n\nIndependently verify the Discovery Agent's brief against the authoritative\nsource text.\n\nDISCOVERY BRIEF:\n{discovery_brief}\n\nAUTHORITATIVE SOURCE:\n{source_text}\n\nReturn a corrected compact verified brief under 1800 characters.\nPreserve exact deadlines, monetary amounts, eligibility requirements,\nrequired technology and submission requirements. Explicitly mark facts\nthat cannot be verified. Do not invent facts.", include_contents='none', output_key='verification_brief')
hard_gate_agent = LlmAgent(name='deterministic_hard_gate_agent', model=MODEL, tools=[eligibility_capital_deadline_gate], instruction='You are the Deterministic Hard Gate Agent.\n\nVERIFIED OPPORTUNITY:\n{verification_brief}\n\nEXACT OPERATOR PROFILE:\n{decision_profile_json}\n\nUse the eligibility_capital_deadline_gate tool exactly as required.\nDeterministic tool results are authoritative and cannot be overridden.\nReturn a concise summary under 700 characters.', include_contents='none', output_key='hard_gate_brief')
investigation_agent = LlmAgent(name='investigation_agent', model=MODEL, instruction='You are the Investigation Agent.\n\nVERIFIED OPPORTUNITY:\n{verification_brief}\n\nEXACT OPERATOR PROFILE:\n{decision_profile_json}\n\nInvestigate the practical execution burden, technical path, expected\nhuman work, automation potential, dependencies, uncertainties and\noperational risks. Return only the highest-value findings under\n1200 characters. Do not repeat the full opportunity description.', include_contents='none', output_key='investigation_brief')
failure_memory_agent = LlmAgent(name='failure_memory_agent', model=MODEL, tools=[failure_memory_similarity_check], instruction='You are the Failure Memory Agent.\n\nVERIFIED OPPORTUNITY:\n{verification_brief}\n\nINVESTIGATION:\n{investigation_brief}\n\nUse the failure_memory_similarity_check tool exactly as required.\nThe authoritative tool result cannot be overridden.\nReturn a concise anti-repeat assessment under 700 characters.', include_contents='none', output_key='failure_memory_brief')
economic_evidence_agent = LlmAgent(name='economic_evidence_agent', model=MODEL, tools=[calculate_unit_economics], instruction='You are the Economic Evidence Agent.\n\nVERIFIED OPPORTUNITY:\n{verification_brief}\n\nINVESTIGATION:\n{investigation_brief}\n\nEXACT OPERATOR PROFILE:\n{decision_profile_json}\n\nUse calculate_unit_economics exactly as required.\nIts deterministic result is authoritative.\nReturn only a compact economic assessment under 700 characters.', include_contents='none', output_key='economic_brief')
final_adjudication_agent = LlmAgent(name='final_adjudication_agent', model=MODEL, tools=[final_evidence_safety_adjudication], instruction='You are the Final Adjudication Agent.\n\nVERIFIED OPPORTUNITY:\n{verification_brief}\n\nHARD GATE:\n{hard_gate_brief}\n\nINVESTIGATION:\n{investigation_brief}\n\nFAILURE MEMORY:\n{failure_memory_brief}\n\nECONOMIC EVIDENCE:\n{economic_brief}\n\nEXACT OPERATOR PROFILE:\n{decision_profile_json}\n\nUse final_evidence_safety_adjudication exactly as required.\nAll deterministic state and tool results are authoritative.\nDo not override them with optimism or narrative judgment.\nReturn a concise final explanation under 800 characters.', include_contents='none', output_key='final_brief')

root_agent = SequentialAgent(
    name="autonomous_opportunity_operator",
    description="Evidence-first opportunity discovery, verification, investigation, and adjudication.",
    sub_agents=[discovery_agent, verification_agent, hard_gate_agent, investigation_agent,
                failure_memory_agent, economic_evidence_agent, final_adjudication_agent],
)
