from pragma.client.websocket import PragmaLightspeedClient
from pragma.config import get_settings

settings = get_settings()

# Create a single instance of the Lightspeed client
lightspeed_client = PragmaLightspeedClient(settings.pragma_websocket_url)
