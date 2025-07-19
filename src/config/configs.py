import os
import yaml
import re

env_var_pattern = re.compile(r'.*?\${(.*?)}.*?')

def env_constructor(loader, node):
    value = loader.construct_scalar(node)
    matches = env_var_pattern.findall(value)
    for match in matches:
        env_value = os.environ.get(match)
        if env_value is None:
            raise ValueError(f"Environment variable '{match}' is not set")
        value = value.replace(f"${{{match}}}", env_value)
    return value

yaml.SafeLoader.add_constructor('!ENV', env_constructor)

with open("configs.yml", "r") as f:
    config = yaml.load(f, Loader=yaml.SafeLoader)

RESNET_EMBEDDING_PATH = config.get("RESNET_EMBEDDING_PATH")
QDRANT_URL = config.get("QDRANT_URL")
VECTOR_SIZE = config.get('VECTOR_SIZE')