import flexirule

@flexirule.processmethod(
    category="Validation",
    description="Test method for registry sync",
    version="1.0",
    return_type="Boolean",
    side_effects="Pure",
    transactional=False,
    creates_new_docs=False
)
def check_registry_sync(context, **kwargs):
    return True
