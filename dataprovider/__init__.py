from .breeze_provider import BreezeDataProvider
# Future: from .upstox_provider import UpstoxDataProvider

# Store active instances so we don't create multiple websockets for the same broker
_provider_instances = {}

def get_data_provider(provider_name: str, session_manager, instrument_mapper):
    provider_name = provider_name.upper()
    
    # Map friendly names to actual provider classes
    if provider_name not in _provider_instances:
        if provider_name == "IDIRECT" or provider_name == "BREEZE":
            _provider_instances[provider_name] = BreezeDataProvider(session_manager, instrument_mapper)
            
        elif provider_name == "UPSTOX":
            # _provider_instances[provider_name] = UpstoxDataProvider(session_manager, instrument_mapper)
            raise NotImplementedError("Upstox Data Provider is not yet implemented")
            
        else:
            raise ValueError(f"Unknown data provider requested: {provider_name}")
            
    return _provider_instances[provider_name]