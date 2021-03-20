class Entity:
    """An entity in a domain."""

    def __init__(self, name, entity_type, attributes=None):
        """Initialize an Entity type."""
        self.name = name
        self.type = entity_type
        self.attributes = attributes or {}

    def add_to_grammar_engine_state(self, grammar_engine, variable_name):
        """Add this entity, and all of its attributes, to the given grammar-engine state."""
        # Set the name to the variable name
        grammar_engine.set_state(variable_name=variable_name, value=self.name)
        # Set all of the entity attributes, if any, to the state using dot notation
        for key, value in self.attributes.items():
            attribute_variable_name = f"{variable_name}.{key}"
            grammar_engine.set_state(variable_name=attribute_variable_name, value=value)

    def __str__(self):
        """Return string representation."""
        return f"{self.name}:{self.type}"

    def __repr__(self):
        """Return string representation."""
        return self.__str__()
