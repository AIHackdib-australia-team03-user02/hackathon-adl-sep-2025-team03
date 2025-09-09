from autogen import AssistantAgent

CRYPTO_SYSTEM = (
    "You are CryptoAgent. Check TLS/SSH/IPsec against ISM crypto controls and Blueprint crypto guidance. "
    "Output JSON: {algorithms_ok:[...], weak_algorithms:[...], key_mgmt:{rotation, storage, ownership}, exceptions:[...]}"
)

def make_crypto_agent(llm_cfg):
    return AssistantAgent("crypto_agent", llm_config=llm_cfg, system_message=CRYPTO_SYSTEM)
