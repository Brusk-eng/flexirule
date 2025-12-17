__version__ = "0.0.1"

from flexirule.ruleflow.core.registry import sync_process_methods
# TODO : The app must provide a regiestry decorator for process_method @flexirule.processmethod(metadata or func that return metadata)
#TODO : Must find how frappe provide decirator and does they use a cache to optimizing executing them and not be load from module when it is requested? and apply the same
#TODO : after update to use that decoration , apply to all methods 
# TODO: for the whole app backend and frontend confirm it use translation like _("python") and for vue/js use __("")