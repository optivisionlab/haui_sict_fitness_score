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

RESNET_EMBEDDING_PATH = config.get("RESNET_EMBEDDING_PATH", "vggface2")
QDRANT_URL = config.get("QDRANT_URL", "http://localhost:6333")
VECTOR_SIZE = config.get('VECTOR_SIZE', 512)
MTCNN_CONFIG = config.get("MTCNN_CONFIG", {})
MONGDB_URI = config.get("MONGDB_URI", "Unknow")
MONGDB_DB = config.get("MONGDB_DB", "Admin")