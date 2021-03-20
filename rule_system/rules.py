class Rule:
    """A Rule in a rule system."""

    def __init__(self, action_name, response_action, action_string, probability, roles, preconditions, effects,
                 response_actions, raw_definition, debug):
        """Initialize a Rule object."""
        self.action_name = action_name
        self.response_action = response_action
        self.action_string = action_string
        self.probability = probability  # Probability rule will fire when its preconditions hold
        self.roles = roles
        self.preconditions = preconditions
        self.effects = effects
        self.response_actions = response_actions
        self.definition = raw_definition
        self.debug = debug

    def __str__(self):
        """Return string representation."""
        return self.definition

    def __repr__(self):
        """Return string representation."""
        return f"${self.action_name}"


class Role:
    """A role in an action, played by some entity."""

    def __init__(self, name, entity_type, optional=False, entity_name_recipe=False):
        """Initialize a Role object."""
        self.name = name
        self.entity_type = entity_type
        self.action_self_reference = name == 'This'
        self.entity_name_recipe = entity_name_recipe  # If the role is bound to a newly created entity upon rule firing
        self.required = (not optional) and not self.action_self_reference and not entity_name_recipe

    def __str__(self):
        """Return string representation."""
        if self.entity_name_recipe:
            # +Note={Writer}'s Note:Prop
            return f"+{self.name}={self.entity_name_recipe}:{self.entity_type}"
        return f"{'?' if not self.required and not self.action_self_reference else ''}{self.name}:{self.entity_type}"

    def __repr__(self):
        """Return string representation."""
        return self.__str__()


class Predicate:
    """A predicate that can serve as a condition or an effect."""

    def __init__(self, template, negated):
        """Initialize a Condition object."""
        self.or_expression = False
        self.ternary_expression = False
        self.template = template
        self.negated = negated
        self.optional_roles = False  # An optional role for a rule, e.g., "Witness*"
        for element in template:
            if type(element) is not str:
                if not element.required and not element.action_self_reference:
                    self.optional_roles = True
                    break
        self.required_roles = {element for element in self.template if type(element) is Role and element.required}
        self.length = len(self.template)
        self._saved_ground_expressions = {}  # We do this to amortize the cost of grounding

    def __str__(self):
        """Return string representation."""
        string_representation = ''
        for i, element in enumerate(self.template):
            if i > 0:
                string_representation += ' '
            if type(element) == Role:
                string_representation += element.name
            else:
                string_representation += element
        return f"{'!' if self.negated else ''}({string_representation})"

    def __repr__(self):
        """Return string representation."""
        return self.__str__()

    def ground(self, bindings):
        """Return a ground expression in the form of this predicate with its variables bound."""
        try:
            return self._saved_ground_expressions[tuple(bindings.items())]
        except KeyError:
            pass
        ground_expression = ''
        for i, element in enumerate(self.template):
            if i > 0:
                ground_expression += ' '
            if type(element) is str:
                ground_expression += element
            else:
                ground_expression += bindings[element.name].name
        self._saved_ground_expressions[tuple(bindings.items())] = ground_expression
        return ground_expression


class OrExpression:
    """An expression representing a logical 'OR' relation over multiple conditions."""

    def __init__(self, conditions):
        """Initialize an OrExpression object."""
        self.or_expression = True
        self.ternary_expression = False
        self.conditions = conditions
        self.optional_roles = False
        self.negated = False
        self.length = max(self.conditions, key=lambda condition: condition.length).length
        self.required_roles = set()
        for condition in conditions:
            self.required_roles |= condition.required_roles
            for element in condition.template:
                if type(element) is not str:
                    if not element.required and not element.action_self_reference:
                        self.optional_roles = True
                        break

    def __str__(self):
        """Return string representation."""
        return " / ".join(str(precondition) for precondition in self.conditions)

    def __repr__(self):
        """Return string representation."""
        return self.__str__()

    def ground(self, bindings):
        """Return a ground expression in the form of this predicate with its variables bound."""
        ground_expression = ' / '.join(condition.ground(bindings=bindings) for condition in self.conditions)
        return ground_expression


class TernaryExpression:
    """A ternary expression containing two conditional effects."""

    def __init__(self, condition, effect_if_true, effect_if_false):
        """Initialize an Effect object."""
        self.or_expression = False
        self.ternary_expression = True
        self.condition = condition
        self.effect_if_true = effect_if_true
        self.effect_if_false = effect_if_false

    def __str__(self):
        """Return string representation."""
        if self.effect_if_true and self.effect_if_false:
            return f"{self.effect_if_true} if {self.condition} else {self.effect_if_false}"
        elif self.effect_if_true:
            return f"{self.effect_if_true} if {self.condition} else ()"
        else:
            return f"() if {self.condition} else {self.effect_if_false}"

    def __repr__(self):
        """Return string representation."""
        return self.__str__()


class ResponseAction:
    """A directive containing the name and bindings for an action that should be attempted following some action."""

    def __init__(self, action_name, action_bindings):
        """Initialize a ResponseAction object."""
        self.action_name = action_name
        self.action_bindings = action_bindings

    def __str__(self):
        """Return string representation."""
        string_representation = f"{self.action_name}("
        for i, (target_role, source_role) in enumerate(self.action_bindings.items()):
            string_representation += f"{target_role}={source_role}"
            if i < len(self.action_bindings) - 1:
                string_representation += ', '
        string_representation += ')'
        return string_representation

    def __repr__(self):
        """Return string representation."""
        return self.__str__()
