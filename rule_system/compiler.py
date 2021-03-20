import re
import itertools
from rule_system.entity import Entity
from rule_system.rules import Rule, Role, Predicate, OrExpression, TernaryExpression, ResponseAction


class Compiler:
    """A compiler for our rule language."""

    @classmethod
    def parse_domain_file(cls, path_to_domain_file):
        """Parse the given domain file to return a dictionary mapping entity types to Entity objects."""
        # Parse the domain-definition file to extract entities and initial facts
        domain_definition = open(path_to_domain_file).read()
        entities = cls._parse_entity_definitions(domain_definition=domain_definition)
        facts = cls._parse_fact_definitions(domain_definition=domain_definition, entities=entities)
        # Construct a domain, formatted as a dictionary mapping entity types to entities
        domain = {}
        for entity in entities:
            try:
                domain[entity.type].append(entity)
            except KeyError:
                domain[entity.type] = [entity]
        # Make sure there's not too entities with the same name
        for entity in entities:
            for other_entity in entities:
                if entity is other_entity:
                    continue
                if entity.name == other_entity.name:
                    raise Exception(f"Multiple entities with the same name: {entity}, {other_entity}")
        return domain, facts

    @staticmethod
    def _parse_entity_definitions(domain_definition):
        """Parse the entity-definitions component of a domain definition to return a list of Entity objects."""
        # First, make sure that the domain definition file is in the expected format. We'll do this using
        # Python's 'assert' statement, which raises an AssertionError if the condition in the left side of the
        # comma evaluates to False, in which case the error message on the right side of the comma will be printed.
        # This form of validation will be used throughout the process of parsing the domain definition.
        assert "<BEGIN ENTITIES>" in domain_definition, "Template definitions file missing '<BEGIN ENTITIES>'."
        assert "<END ENTITIES>" in domain_definition, "Template definitions file missing '<END ENTITIES>'."
        assert domain_definition.index("<BEGIN ENTITIES>") < domain_definition.index("<END ENTITIES>"), (
            "'<BEGIN ENTITIES>' comes after <END ENTITIES> in template definitions file."
        )
        # Extract the entity definitions by taking the substring between the index of the start marker
        # ("<BEGIN ENTITIES>") and the end marker ("<END ENTITIES>"). Note that the str.index() function returns
        # the index of the first character of the first instance of the substring that is passed to it; as such,
        # we'll add to the start index the length of the start marker, so that we don't include the marker
        # itself in the extracted content.
        entity_definitions_start_index = domain_definition.index("<BEGIN ENTITIES>") + len("<BEGIN ENTITIES>")
        entity_definitions_end_index = domain_definition.index("<END ENTITIES>")
        entity_definitions = domain_definition[entity_definitions_start_index:entity_definitions_end_index]
        # Next, iterate over each line in the entity definitions to attempt to form an Entity object for any line that
        # doesn't consists of non-whitespace characters or begin with '#' (our comment symbol). We'll append each
        # Entity object to the list of entities.
        entities = []
        for line in entity_definitions.split('\n'):
            if '=' in line:
                continue
            line = line.strip()  # Remove all whitespace on either side of the line
            if not line:  # The line contained only whitespace, so now it's an empty string
                continue  # Move on to the next iteration of the 'for' loop, i.e., to the next line
            if line.startswith('#'):  # It's a comment
                continue
            while '\t\t' in line:  # Replace consecutive tab characters with a single tab character
                line = line.replace('\t\t', '\t')
            # If we get to here, this must be an entity definition, though it may be malformed. Here, we'll use
            # a try-except block to safely attempt to parse it as if it were in the expected format. If it's
            # not in the expected format, i.e., it doesn't have two fields separated by a single colon, a
            # ValueError will be raised indicating that splitting on the colon character did not produce exactly
            # two components. If this happens, we'll raise an Exception with an error message including the
            # malformed entity definition.
            try:
                entity_name, entity_type = line.split(':')
            except ValueError:
                # Let's form a nice error message that includes the exact entity definition that was malformed. We'll
                # do this using a Python f-String (http://zetcode.com/python/fstring/).
                if ':' not in line:
                    error_message = f"Malformed entity definition (no ':' delimiter): '{line}'"
                else:  # It has too few or too many components; there should be exactly two: name and values
                    error_message = f"Malformed entity definition: '{line}'"
                raise Exception(error_message)
            # At this point, there's two ways that this entity definition could be malformed: 1) the entity name is an
            # empty string or comprises only whitespace, or 2) the entity type is an empty string or comprises only
            # whitespace. We'll check for both and raise an Exception, with an informative error message, in each case.
            entity_name = entity_name.strip()  # Remove leading or trailing whitespace
            entity_type = entity_type.strip()
            if not entity_name:  # It comprised only whitespace
                error_message = f"Entity definition includes no name: {line}"
                raise Exception(error_message)
            if not entity_type:  # It comprised only whitespace
                error_message = f"Entity definition includes no values: {line}"
                raise Exception(error_message)
            # If we get to here, we have a valid entity definition. Let's now parse out any attributes defined
            # for this entity.
            entity_attributes = {}
            for attribute_line in entity_definitions.split('\n'):
                attribute_line = attribute_line.strip()
                if '=' not in attribute_line:
                    continue
                raw_attribute, value = attribute_line.split('=')
                if '.' not in raw_attribute:
                    raise Exception(f"Malformed attribute: {attribute_line}")
                attribute_entity_name, attribute_name = raw_attribute.split('.')
                if attribute_entity_name != entity_name:
                    continue
                attribute_name = attribute_name.rstrip()
                value = value.lstrip()
                entity_attributes[attribute_name] = value
            # Finally, Construct an Entity object and add it to our list of entities
            entity_object = Entity(name=entity_name, entity_type=entity_type, attributes=entity_attributes)
            entities.append(entity_object)
        return entities

    @classmethod
    def _parse_fact_definitions(cls, domain_definition, entities):
        """Parse the fact-definitions component of a domain definition to return a list of Fact objects."""
        # First, make sure that the template definitions file is in the expected format
        assert "<BEGIN FACTS>" in domain_definition, "Domain definition file missing '<BEGIN FACTS>'."
        assert "<END FACTS>" in domain_definition, "Domain definition file missing '<END FACTS>'."
        assert domain_definition.index("<BEGIN FACTS>") < domain_definition.index("<END FACTS>"), (
            "'<BEGIN FACTS>' comes after <END FACTS> in domain definition file."
        )
        # Extract the fact definitions
        fact_definitions_start_index = domain_definition.index("<BEGIN FACTS>") + len("<BEGIN FACTS>")
        fact_definitions_end_index = domain_definition.index("<END FACTS>")
        fact_definitions = domain_definition[fact_definitions_start_index:fact_definitions_end_index]
        # Next, iterate over each line in the fact definitions to attempt to form a Fact object for any line that
        # doesn't consists of non-whitespace characters or begin with '#' (our comment symbol). We'll append each
        # Fact object to the list of facts.
        facts = set()
        for line in fact_definitions.split('\n'):
            line = line.strip()  # Remove all whitespace on either side of the line
            if not line:  # The line contained only whitespace, so now it's an empty string
                continue  # Move on to the next iteration of the 'for' loop, i.e., to the next line
            if line.startswith('#'):  # It's a comment
                continue
            # If we get to here, this must be a fact definition, though it may be malformed due to mismatched brackets.
            # Again, we'll use a try-except block to safely attempt to parse it as if it were in the expected format.
            if line.count('<') != line.count('>'):
                error_message = f"Malformed fact definition (unbalanced brackets): '{line}'"
                raise Exception(error_message)
            # Now, let's parse the fact definition to form a grounded fact expression
            fact = cls._parse_fact_definition(fact_definition=line, entities=entities)
            # As a final check, make sure that there's duplicate facts, which might cue an authoring error
            if fact in facts:
                raise Exception(f"Duplicate fact in the domain definition: {line}")
            # If we get here, it's a valid, unique fact, so append it to our list
            facts.add(fact)
        return facts

    @staticmethod
    def _parse_fact_definition(fact_definition, entities):
        """Parse the given fact definition, using the list of entities, to return a Fact object."""
        # Infer fact expression
        expression = ''
        parsing_entity_reference = False
        referenced_entity_name = ''
        for component in re.split('(<|>)', fact_definition):
            if not component:
                continue
            if component == '<':
                parsing_entity_reference = True
                continue
            if component == '>':
                parsing_entity_reference = False
                try:
                    next(entity for entity in entities if entity.name == referenced_entity_name)
                except StopIteration:
                    error_message = f'Fact references undefined entity "{referenced_entity_name}": {fact_definition}'
                    raise Exception(error_message)
                expression += referenced_entity_name
                referenced_entity_name = ''
                continue
            if parsing_entity_reference:
                referenced_entity_name += component
            else:  # Non-variable component
                if component[0] != component[0].lower():
                    error_message = "Capital letters are reserved for role references, but one appeared outside a "
                    error_message += f"role reference in this fact: {fact_definition}."
                    raise Exception(error_message)
                expression += component
        # Return the fact tuple
        fact = expression
        return fact

    @classmethod
    def parse_rules_file(cls, path_to_rules_file):
        """Parse the given rules file to return a list of Rule objects."""
        lines = open(path_to_rules_file).readlines()
        # Remove blank lines
        lines = [line for line in lines if line.strip()]
        # Remove comments
        lines = [line for line in lines if not line.lstrip().startswith('#')]
        # Reduce whitespace
        blob = ''.join(lines)
        blob = blob.replace('\t', ' ')
        while '  ' in blob:
            blob = blob.replace('  ', ' ')
        # Break into individual rule definitions
        rule_definitions = [line.strip() for line in blob.split('$') if line]
        # Parse each rule definition
        rule_objects = []
        for rule_definition in rule_definitions:
            rule_object = cls._parse_rule_definition(rule_definition=rule_definition)
            rule_objects.append(rule_object)
        # Make sure that no rule contains malformed response-action declarations
        for rule in rule_objects:
            for response_action in rule.response_actions:
                if not any(rule for rule in rule_objects if rule.action_name == response_action.action_name):
                    error_message = f"Rule '${rule.action_name}' includes a response action referring to rule "
                    error_message += f"'${response_action.action_name}', but no such rule has been defined"
                    raise Exception(error_message)
                response_action_rule = (
                    next(rule for rule in rule_objects if rule.action_name == response_action.action_name)
                )
                for target_role, source_role in response_action.action_bindings.items():
                    if not any(role for role in response_action_rule.roles if role.name == target_role):
                        error_message = f"Rule '${rule.action_name}' includes a response action that references an "
                        error_message += f"undefined role '{target_role}' for the response action: {response_action}"
                        raise Exception(error_message)
                    if not any(role for role in rule.roles if role.name == source_role):
                        error_message = f"Rule '${rule.action_name}' includes a response action that references an "
                        error_message += f"undefined role '{source_role}' for '${rule.action_name}': {response_action}"
                        raise Exception(error_message)
                for role in response_action_rule.roles:
                    if not role.required:
                        continue
                    if role.name not in response_action.action_bindings:
                        error_message = f"Rule '${rule.action_name}' includes a response action that is missing the "
                        error_message += f"role '{role}' for '${rule.action_name}': {response_action}"
                        raise Exception(error_message)
        # Make sure that each action has only one rule
        for rule in rule_objects:
            for other_rule in rule_objects:
                if rule is other_rule:
                    continue
                if rule.action_name == other_rule.action_name:
                    raise Exception(f"Multiple rules for action: ${rule.action_name}")
        return rule_objects

    @classmethod
    def _parse_rule_definition(cls, rule_definition):
        """Parse the given rule definition."""
        # Parse action name and action string
        action_name, action_string, *action_definition_body = rule_definition.split('\n')
        action_name = action_name.rstrip()
        debug_action = action_name.endswith(' debug')
        action_name = action_name[:-len(' debug')] if debug_action else action_name
        response_action = action_name.endswith('(response)')
        action_name = action_name.split()[0]
        # Parse roles, preconditions, effects, triggers
        roles = []
        preconditions = []
        effects = []
        response_actions = []
        action_definition_body = '\n'.join(action_definition_body)
        definition_components = re.split('(prob:|roles:|preconditions:|effects:|responses:)', action_definition_body)
        parsing_probability = False
        parsing_roles = False
        parsing_preconditions = False
        parsing_effects = False
        parsing_response_actions = False
        rule_probability = 1.0
        for component in definition_components:
            if not component.strip():
                continue
            if component == "prob:":
                parsing_probability = True
                continue
            if component == "roles:":
                parsing_roles = True
                continue
            if component == "preconditions:":
                parsing_preconditions = True
                continue
            if component == "effects:":
                parsing_effects = True
                continue
            if component == "responses:":
                parsing_response_actions = True
                continue
            if parsing_probability:
                try:
                    rule_probability = float(component.strip())
                except ValueError:
                    error_message = f"Malformed probability value for rule ${action_name}: {component}"
                    raise Exception(error_message)
                parsing_probability = False
            if parsing_roles:
                parsing_roles = False
                role_definitions = component.split('\n')
                for role_definition in role_definitions:
                    if not role_definition.strip():
                        continue
                    if len([part for part in role_definition.split(':') if part.strip()]) < 2:
                        raise Exception(f"Malformed role definition in '${action_name}': {role_definition}")
                    role_object = cls._parse_role_definition(role_definition=role_definition)
                    roles.append(role_object)
                roles.append(Role(name='This', entity_type='Action'))
            elif parsing_preconditions:
                parsing_preconditions = False
                precondition_definitions = component.split('\n')
                for precondition_definition in precondition_definitions:
                    if not precondition_definition.strip():
                        continue
                    if '*:' in precondition_definition:
                        # There's a macro role, e.g., "*:Character" -- so generate a series of
                        # preconditions accordingly
                        macro_generated_precondition_definitions = cls._macro_generate_precondition_definitions(
                            precondition_definition=precondition_definition,
                            roles=roles
                        )
                        for macro_generated_precondition_definition in macro_generated_precondition_definitions:
                            precondition_object = cls._parse_condition_definition(
                                condition_definition=macro_generated_precondition_definition,
                                action_name=action_name,
                                roles=roles
                            )
                            preconditions.append(precondition_object)
                    else:
                        precondition_object = cls._parse_condition_definition(
                            condition_definition=precondition_definition,
                            action_name=action_name,
                            roles=roles
                        )
                        preconditions.append(precondition_object)
            elif parsing_effects:
                parsing_effects = False
                effect_definitions = component.split('\n')
                for effect_definition in effect_definitions:
                    if not effect_definition.strip():
                        continue
                    if '*:' in effect_definition:
                        # There's a macro role, e.g., "*:Character" -- so generate a series of effects accordingly
                        macro_generated_effect_definitions = cls._macro_generate_effect_definitions(
                            effect_definition=effect_definition,
                            roles=roles
                        )
                        for macro_generated_effect_definition in macro_generated_effect_definitions:
                            effect_object = cls._parse_effect_definition(
                                effect_definition=macro_generated_effect_definition,
                                action_name=action_name,
                                roles=roles
                            )
                            effects.append(effect_object)
                    else:
                        effect_object = cls._parse_effect_definition(
                            effect_definition=effect_definition,
                            action_name=action_name,
                            roles=roles
                        )
                        effects.append(effect_object)
            elif parsing_response_actions:
                parsing_response_actions = False
                response_action_definitions = component.split('\n')
                for response_action_definition in response_action_definitions:
                    if not response_action_definition.strip():
                        continue
                    response_action_bindings = {}
                    response_action_definition = response_action_definition.strip()
                    response_action_name, raw_response_action_bindings = (
                        response_action_definition.rstrip(' )').split('(')
                    )
                    for raw_binding in raw_response_action_bindings.replace(' ', '').split(','):
                        target_role, source_role = raw_binding.split('=')
                        response_action_bindings[target_role] = source_role
                    response_action_object = cls._parse_response_action_definition(
                        response_action_definition=response_action_definition
                    )
                    response_actions.append(response_action_object)
        # Before constructing the Rule object, make sure the action string is well-formed
        if action_string.count('{') != action_string.count('}'):
            error_message = f"Malformed action string in rule '${action_name}' "
            error_message += f"(unbalanced curly braces): '{action_string}'"
            raise Exception(error_message)
        for role_reference in re.findall(r'\{.*?\}', action_string):
            role_name = role_reference[1:-1]  # Strip curly braces
            if not any(role for role in roles if role.name == role_name):
                error_message = f"Action string in rule '${action_name}' references undefined role '{role_name}"
                raise Exception(error_message)
        rule_object = Rule(
            action_name=action_name,
            response_action=response_action,
            action_string=action_string,
            probability=rule_probability,
            roles=roles,
            preconditions=preconditions,
            effects=effects,
            response_actions=response_actions,
            raw_definition=rule_definition,
            debug=debug_action
        )
        return rule_object

    @staticmethod
    def _macro_generate_precondition_definitions(precondition_definition, roles):
        """Expand macro roles in the given precondition definition to produce a series of precondition definitions."""
        # Gather all macro roles and the roles to which they refer
        macro_roles = re.findall('(\*:[A-Z][a-z]*\w)', precondition_definition)
        macro_role_reference_roles = []
        for macro_role in macro_roles:
            roles_referenced_by_this_macro_role = []
            macro_role_entity_type = macro_role.split(':')[1]
            for role in roles:
                if role.entity_type == macro_role_entity_type:
                    roles_referenced_by_this_macro_role.append(role.name)
            macro_role_reference_roles.append(roles_referenced_by_this_macro_role)
        # Expand these macro roles to form new effect definitions
        macro_generated_precondition_definitions = []
        for expansion in itertools.product(*macro_role_reference_roles):
            macro_generated_precondition_definition = precondition_definition
            for i, reference_role in enumerate(expansion):
                macro_role = macro_roles[i]
                macro_generated_precondition_definition = (
                    macro_generated_precondition_definition.replace(macro_role, reference_role)
                )
            macro_generated_precondition_definitions.append(macro_generated_precondition_definition)
        return macro_generated_precondition_definitions

    @staticmethod
    def _macro_generate_effect_definitions(effect_definition, roles):
        """Expand macro roles in the given effect definition to produce a series of effect definitions."""
        # Gather all macro roles and the roles to which they refer
        macro_roles = re.findall('(\*:[A-Z][a-z]*\w)', effect_definition)
        macro_role_reference_roles = []
        for macro_role in macro_roles:
            roles_referenced_by_this_macro_role = []
            macro_role_entity_type = macro_role.split(':')[1]
            for role in roles:
                if role.entity_type == macro_role_entity_type:
                    roles_referenced_by_this_macro_role.append(role.name)
            macro_role_reference_roles.append(roles_referenced_by_this_macro_role)
        # Expand these macro roles to form new effect definitions
        macro_generated_effect_definitions = []
        for expansion in itertools.product(*macro_role_reference_roles):
            macro_generated_effect_definition = effect_definition
            for i, reference_role in enumerate(expansion):
                macro_role = macro_roles[i]
                macro_generated_effect_definition = (
                    macro_generated_effect_definition.replace(macro_role, reference_role)
                )
            macro_generated_effect_definitions.append(macro_generated_effect_definition)
        return macro_generated_effect_definitions

    @staticmethod
    def _parse_role_definition(role_definition):
        """Parse the given role definition to return a Role object."""
        role_definition = role_definition.strip()
        if role_definition.startswith('+'):  # Ex: +Note={Writer}'s Note:Prop
            role_name, entity_name_and_type = role_definition[1:].split('=')
            entity_name_recipe, entity_type = entity_name_and_type.split(':')
            role_object = Role(name=role_name, entity_type=entity_type, entity_name_recipe=entity_name_recipe)
            return role_object
        role_name, entity_type = role_definition.split(':')
        role_is_optional = role_name.startswith('?')
        if role_is_optional:
            role_name = role_name[1:]
        if role_name == 'This':
            error_message = "The role name 'This' is reserved for action self-referencing. It can't be used in "
            error_message += "the 'roles' section of a rule."
        entity_type = entity_type.strip()
        role_object = Role(name=role_name, entity_type=entity_type, optional=role_is_optional)
        return role_object

    @classmethod
    def _parse_condition_definition(cls, condition_definition, action_name, roles):
        """Parse the given precondition definition to return a Condition object."""
        condition_definition = condition_definition.lstrip().rstrip()
        if condition_definition.count('(') != condition_definition.count(')') != 1:
            raise Exception(f"Missing/unbalanced parentheses in '${action_name}' precondition: {condition_definition}")
        if not condition_definition.startswith('(') and not condition_definition.startswith('!('):
            raise Exception(f"Precondition for '${action_name}' doesn't start with '(' or '!(': {condition_definition}")
        if '/' in condition_definition:  # It's an 'OR' expression
            raw_conditions = condition_definition.split('/')
            conditions_in_or_expression = []
            for raw_precondition in raw_conditions:
                condition_object = cls._parse_condition_definition(
                    condition_definition=raw_precondition,
                    action_name=action_name,
                    roles=roles
                )
                conditions_in_or_expression.append(condition_object)
            or_expression = OrExpression(conditions=conditions_in_or_expression)
            return or_expression
        raw_precondition = condition_definition.strip()
        negated = raw_precondition[0] == '!'
        raw_precondition = raw_precondition.lstrip("!( ").rstrip(" )")
        template = []
        for word in raw_precondition.split():
            if word[0] == word[0].lower():
                template.append(word)
            else:  # It's a role reference
                try:
                    role = next(role for role in roles if role.name == word)
                    template.append(role)
                except StopIteration:
                    roles_str = ', '.join(role.name for role in roles)
                    error_message = f"Rule definition for '{action_name}' references a role '{word}' "
                    error_message += f"in precondition '{raw_precondition}' that is not introduced in "
                    error_message += f"the action's roles: {roles_str}"
                    raise Exception(error_message)
        condition_object = Predicate(template=template, negated=negated)
        return condition_object

    @classmethod
    def _parse_effect_definition(cls, effect_definition, action_name, roles):
        """Parse the given effect definition to return an Effect object."""
        effect_definition = effect_definition.lstrip().rstrip()
        if effect_definition.count('(') != effect_definition.count(')') != 1:
            raise Exception(f"Missing/unbalanced parentheses in '${action_name}' effect: {effect_definition}")
        if not effect_definition.startswith('(') and not effect_definition.startswith('!('):
            raise Exception(f"Effect for '${action_name}' doesn't start with '(' or '!(': {effect_definition}")
        if effect_definition == '()':
            return None
        if effect_definition.count('(') == 3:
            raw_effect_if_true, raw_condition, raw_effect_if_false = re.findall(r'\(.*?\)', effect_definition)
            condition = cls._parse_condition_definition(
                condition_definition=raw_condition,
                action_name=action_name,
                roles=roles
            )
            effect_if_true = cls._parse_effect_definition(
                effect_definition=raw_effect_if_true,
                action_name=action_name,
                roles=roles
            )
            effect_if_false = cls._parse_effect_definition(
                effect_definition=raw_effect_if_false,
                action_name=action_name,
                roles=roles
            )
            ternary_expression = TernaryExpression(
                condition=condition,
                effect_if_true=effect_if_true,
                effect_if_false=effect_if_false
            )
            return ternary_expression
        raw_effect = effect_definition.strip()
        negated = raw_effect[0] == '!'
        raw_effect = raw_effect.lstrip("!( ").rstrip(" )")
        template = []
        for word in raw_effect.split():
            if word[0] == word[0].lower():
                template.append(word)
            else:  # It's a role reference
                try:
                    role = next(role for role in roles if role.name == word)
                    template.append(role)
                except StopIteration:
                    error_message = f"Rule definition for '{action_name}' references a role '{word}' "
                    error_message += f"in effect '{raw_effect}' that is not introduced in "
                    error_message += "the action's roles."
                    raise Exception(error_message)
        effect_object = Predicate(template=template, negated=negated)
        return effect_object

    @staticmethod
    def _parse_response_action_definition(response_action_definition):
        """Parse the given response-action definition to return a ResponseAction object."""
        response_action_bindings = {}
        response_action_definition = response_action_definition.strip()
        response_action_name, raw_response_action_bindings = response_action_definition.rstrip(' )').split('(')
        for raw_binding in raw_response_action_bindings.replace(' ', '').split(','):
            target_role, source_role = raw_binding.split('=')
            response_action_bindings[target_role] = source_role
        response_action_object = ResponseAction(
            action_name=response_action_name,
            action_bindings=response_action_bindings
        )
        return response_action_object
