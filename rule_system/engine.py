import re
import sys
import time
import random
import itertools
import rule_system.utils as utils
import rule_system.config as config
from rule_system.compiler import Compiler
from rule_system.entity import Entity


class RuleEngine:
    """An engine for executing a rule system."""

    def __init__(self, path_to_domain_file, path_to_rules_file, shuffle_randomly=True, random_seed=None):
        """Initialize a RuleEngine object."""
        self.domain, initial_facts = Compiler.parse_domain_file(path_to_domain_file=path_to_domain_file)
        self.rules = Compiler.parse_rules_file(path_to_rules_file=path_to_rules_file)
        self.shuffle_randomly = shuffle_randomly
        self.working_memory = WorkingMemory(initial_facts=initial_facts)
        self.actions = []  # A list of Action objects, representing all the actions that have occurred
        # If we received a random seed, use it to seed the random module
        if random_seed is not None:
            random.seed(random_seed)
        else:
            random.seed(time.time())  # Seed with the current UNIX time to introduce randomness

    def __str__(self):
        """Return string representation."""
        return "Rule Engine"

    def __repr__(self):
        """Return string representation."""
        return self.__str__()

    @property
    def entities(self):
        """Return all entities across the domain."""
        entities = []
        for entity_type in self.domain:
            entities += self.domain[entity_type]
        return entities

    def entity_by_name(self, entity_name):
        """Return the entity with the given name, if any."""
        for entity in self.entities:
            if entity.name == entity_name:
                return entity
        return None

    def rule_by_action_name(self, action_name):
        """Return the rule with the given action name, if any."""
        for rule in self.rules:
            if rule.action_name == action_name:
                return rule
        return None

    def execute(self, n=1):
        """Execute up to n rules, thereby generating up to n actions."""
        if config.VERBOSITY >= 3:
            print(f"Attempting to execute up to {n} rules...")
        for _ in range(n):
            self._attempt_rule_execution()

    def _attempt_rule_execution(self):
        """Attempt to execute a single rule."""
        if self.shuffle_randomly:
            if config.VERBOSITY >= 3:
                print(f"Shuffled rule order")
            random.shuffle(self.rules)
        pruned_rules_pool = self._prune_rules_pool(rules=list(self.rules))
        for rule in pruned_rules_pool:
            config.VERBOSITY = 3 if rule.debug else config.VERBOSITY_
            if config.VERBOSITY >= 2:
                print(f"Testing rule '${rule.action_name}'...")
            # If this is a response action, we don't attempt to execute it during the normal rule-testing loop,
            # so move on. (Response actions are only tested as the actions to which they response occur.)
            if rule.response_action:
                if config.VERBOSITY >= 3:
                    print(f"  Ignoring because it's a response rule")
                continue
            # Before going further with this rule, make sure that there's at least one viable entity in the domain
            # for each of its required roles. This may not be the case if the rule, for instance, references an action
            # when we haven't had any actions yet.
            if any(role for role in rule.roles if role.required and role.entity_type not in self.domain):
                if config.VERBOSITY >= 3:
                    problem_role = next(role for role in rule.roles if role.entity_type not in self.domain)
                    message = f"Ignoring because its role '{problem_role}' can't be bound "
                    message += f"(no '{problem_role.entity_type}' entities are in the domain currently)"
                    print(f"  {message}")
                continue
            preconditions_to_ignore = set(self._get_preconditions_to_ignore(rule))
            for bindings in self._compile_candidate_bindings(rule=rule):
                if config.VERBOSITY >= 3:
                    bindings_str = ', '.join(f"{role}={entity.name}" for role, entity in bindings.items())
                    print(f"  Trying bindings: {bindings_str}")
                if self._triggers(rule=rule, bindings=bindings, preconditions_to_ignore=preconditions_to_ignore):
                    if config.VERBOSITY >= 3:
                        print("  All preconditions hold!")
                        print(f"  Testing rule probability ({rule.probability})")
                    if random.random() < rule.probability:
                        if config.VERBOSITY >= 3:
                            print(f"  Triggered rule!")
                        bindings = self._bind_optional_roles(rule=rule, bindings=bindings)
                        self._fire(rule=rule, bindings=bindings)
                    else:
                        if config.VERBOSITY >= 3:
                            print(f"  Did not trigger rule (probability not met)")
                    return

    def _prune_rules_pool(self, rules):
        """Prune the rules pool by eliminating rules for whom at least one role-less precondition fails."""
        pruned_rules_pool = list(rules)
        for rule in rules:
            for precondition in rule.preconditions:
                if precondition.required_roles or precondition.optional_roles:
                    continue
                if not self.working_memory.holds(condition=precondition, bindings={}):
                    pruned_rules_pool.remove(rule)
                    break
        return pruned_rules_pool

    @staticmethod
    def _get_preconditions_to_ignore(rule):
        """Return a list of preconditions that will necessarily hold for all entities in the pruned candidates list."""
        preconditions_to_ignore = []
        for precondition in rule.preconditions:
            if len(precondition.required_roles) != 1:
                continue
            if precondition.optional_roles:
                continue
            preconditions_to_ignore.append(precondition)
        return preconditions_to_ignore

    def _compile_candidate_bindings(self, rule):
        """Return all possible bindings for the given rule."""
        required_roles_in_order = [role for role in rule.roles if role.required and not role.action_self_reference]
        role_candidate_pools = []
        for role in required_roles_in_order:
            candidate_pool = list(self.domain[role.entity_type])
            pruned_candidate_pool = self._prune_role_candidate_pool(rule=rule, role=role, candidate_pool=candidate_pool)
            if not pruned_candidate_pool:  # This role can't be filled, so return an empty list
                return []
            if self.shuffle_randomly:
                random.shuffle(pruned_candidate_pool)
            role_candidate_pools.append(pruned_candidate_pool)
        candidate_bindings = itertools.product(*role_candidate_pools)
        for bindings in candidate_bindings:
            if len(bindings) != len(set(bindings)):
                # There's an entity bound to multiple roles, so ignore this binding
                continue
            bindings_in_dictionary_format = {}
            for i, entity in enumerate(bindings):
                bindings_in_dictionary_format[required_roles_in_order[i].name] = entity
            yield bindings_in_dictionary_format

    def _prune_role_candidate_pool(self, rule, role, candidate_pool):
        """Removing entities from the candidate pool for whom preconditions referencing only this role fail."""
        pruned_candidate_pool = list(candidate_pool)
        for precondition in rule.preconditions:
            if role not in precondition.required_roles:
                continue
            if len(precondition.required_roles) != 1:
                continue
            if precondition.optional_roles:
                continue
            for candidate in candidate_pool:
                if not self.working_memory.holds(condition=precondition, bindings={role.name: candidate}):
                    try:
                        pruned_candidate_pool.remove(candidate)
                    except ValueError:
                        continue
        return pruned_candidate_pool

    def _triggers(self, rule, bindings, preconditions_to_ignore=None):
        """Return whether the given rule triggers."""
        for precondition in rule.preconditions:
            if preconditions_to_ignore and precondition in preconditions_to_ignore:
                continue
            if precondition.optional_roles:
                continue
            if config.VERBOSITY >= 3:
                print(f"  Evaluating precondition: {precondition}")
            if not self.working_memory.holds(condition=precondition, bindings=bindings):
                if config.VERBOSITY >= 3:
                    print(utils.red(f"    Doesn't hold: {precondition.ground(bindings=bindings)}"))
                return False
            if config.VERBOSITY >= 3:
                print(f"    Holds: {precondition.ground(bindings=bindings)}")
        return True

    def _bind_optional_roles(self, rule, bindings):
        """Return updated bindings potentially binding entities to optional (zero-or-more) roles."""
        for role in rule.roles:
            if role.entity_name_recipe:
                continue  # We'll handle these below, in case the name depends on an optional role
            if not role.required and not role.action_self_reference:
                entity = self._bind_optional_role(rule=rule, role=role, bindings=bindings)
                if entity:
                    bindings[role.name] = entity
        for role in rule.roles:
            if role.entity_name_recipe:
                entity = self._bind_entity_creation_role(role=role, bindings=bindings)
                bindings[role.name] = entity
        return bindings

    def _bind_entity_creation_role(self, role, bindings):
        """Return a new entity that was created to fill this role."""
        # First, resolve the entity name
        this_module = sys.modules[__name__]
        for role_name, entity in bindings.items():
            entity_name_with_escape_characters = entity.name.replace("'", "\\'").replace('"', '\\"')
            setattr(this_module, "_" + role_name, entity_name_with_escape_characters)
        entity_name_recipe_with_escape_characters = role.entity_name_recipe.replace("'", "\\'").replace('"', '\\"')
        format_string = f"f'{entity_name_recipe_with_escape_characters}'".replace("{", "{_")
        resolved_entity_name = eval(format_string)
        # If some entity already has that name, derive a unique one from it
        suffix = 0
        base_entity_name = resolved_entity_name
        while any(entity for entity in self.entities if entity.name == resolved_entity_name):
            suffix += 1
            resolved_entity_name = f"{base_entity_name} ({suffix})"
        # Next, create the new entity
        new_entity = Entity(name=resolved_entity_name, entity_type=role.entity_type)
        # Add it to the domain
        try:
            self.domain[new_entity.type].append(new_entity)
        except KeyError:
            self.domain[new_entity.type] = [new_entity]
        # Return the entity
        return new_entity

    def _bind_optional_role(self, rule, role, bindings):
        """Return an entity, if any, bound to the given optional role."""
        if config.VERBOSITY >= 3:
            print(f"  Attempting to bind the optional role '{role}'")
        try:
            candidate_pool = list(self.domain[role.entity_type])
        except KeyError:
            if config.VERBOSITY >= 3:
                print(f"  There are currently no entities of type '{role.entity_type} in the domain")
            return None
        for entity in candidate_pool:
            if entity in bindings.values():  # The entity is already bound
                continue
            # Test all preconditions that reference this entity
            test_bindings = dict(bindings)
            test_bindings.update({role.name: entity})
            preconditions_hold = True
            for precondition in rule.preconditions:
                if not self.working_memory.holds(condition=precondition, bindings=test_bindings):
                    preconditions_hold = False
                    break
            if preconditions_hold:
                return entity
        return None

    def _fire(self, rule, bindings):
        """Fire the given rule, i.e., execute its effects and test any rules that it triggers."""
        # Create an 'Action' entity for the action associated with the rule
        bindings = self._spawn_action(rule=rule, bindings=bindings)
        # Execute the rule effects
        for effect in rule.effects:
            # If it's a ternary expression, evaluate the condition to retrieve the proper effect
            if effect.ternary_expression:
                if config.VERBOSITY >= 3:
                    print(f"Evaluating ternary expression: {effect}")
                if self.working_memory.holds(condition=effect.condition, bindings=bindings):
                    effect = effect.effect_if_true
                else:
                    effect = effect.effect_if_false
                if not effect:  # Example: (Rejecter hurt Apologizer) if !(Apologizer is forgiving) else ()
                    continue
            if effect.negated:
                self.working_memory.delete(predicate=effect, bindings=bindings)
            else:
                self.working_memory.add(predicate=effect, bindings=bindings)
        # Test any response actions
        for response_action in rule.response_actions:
            if config.VERBOSITY >= 2:
                print(f"Testing rule for response action '${response_action.action_name}'")
            # Retrieve rule for that response action (it's guaranteed to exist at compile time)
            response_action_rule = next(rule for rule in self.rules if rule.action_name == response_action.action_name)
            # Prepare the bindings to pass to that rule
            response_action_bindings = {}
            for target_role, source_role in response_action.action_bindings.items():
                response_action_bindings[target_role] = bindings[source_role]
            # Attempt to execute the rule for the response action
            if self._triggers(rule=response_action_rule, bindings=response_action_bindings):
                if config.VERBOSITY >= 3:
                    print("  All preconditions hold!")
                    print(f"  Testing rule probability ({rule.probability})")
                if random.random() < rule.probability:
                    if config.VERBOSITY >= 3:
                        print(f"  Triggered rule!")
                    self._fire(rule=response_action_rule, bindings=response_action_bindings)
                else:
                    if config.VERBOSITY >= 3:
                        print(f"  Did not trigger rule (probability not met)")

    def _spawn_action(self, rule, bindings):
        """Spawn a new action associated with the given rule, which just fired."""
        # First, resolve the rule string
        this_module = sys.modules[__name__]
        for role_name, entity in bindings.items():
            entity_name_with_escape_characters = entity.name.replace("'", "\\'").replace('"', '\\"')
            setattr(this_module, "_" + role_name, entity_name_with_escape_characters)
        format_string = f"f'{rule.action_string}'".replace("{", "{_")
        resolved_action_string = eval(format_string)[1:-1]
        # Next, form an action entity that can be bound to the special "This" role
        action_entity = Entity(name=resolved_action_string, entity_type='Action')
        if 'Action' not in self.domain:
            self.domain['Action'] = []
        self.domain['Action'].append(action_entity)
        # Add the action into the bindings, using the special "This" role
        bindings['This'] = action_entity
        # Now, construct an Action object and save it to the list of actions
        action_object = Action(action_name=rule.action_name, action_string=resolved_action_string, bindings=bindings)
        self.actions.append(action_object)
        # Print out the action
        if config.VERBOSITY >= 1:
            print(utils.yellow(resolved_action_string))
        return bindings

    def produced_action(self, action_name):
        """Return whether this engine has produced an action with the given action name."""
        for action in self.actions:
            if action.name == action_name:
                return True
        return False

    def actions_involving(self, entity_name):
        """Return a list of all actions involving the entity with the given name."""
        entity = self.entity_by_name(entity_name=entity_name)
        return [action for action in self.actions if entity in action.entities]

    def debug(self, action_name, bindings_string):
        """Test execution of the rule associated with the action name, given the binding string."""
        rule = self.rule_by_action_name(action_name=action_name)
        if not rule:
            raise Exception(f"Couldn't find rule with action name '{action_name}'")
        bindings = {}
        for binding in bindings_string.replace(', ', ',').split(','):
            role_name, entity_name = binding.split('=')
            entity = self.entity_by_name(entity_name=entity_name)
            if not entity:
                raise Exception(f"Couldn't find entity named '{entity_name}'")
            bindings[role_name] = entity
        config.VERBOSITY = 3
        print(utils.green(f"\n\nTesting rule ${action_name} with debugging on."))
        if self._triggers(rule=rule, bindings=bindings):
            print("  All preconditions hold!")
            print(f"  Testing rule probability ({rule.probability})")
            if random.random() < rule.probability:
                print("  Triggered rule!")
                print("    But I'm not executing it, because this is for debugging only.")
                self._bind_optional_roles(rule=rule, bindings=bindings)
            else:
                print(f"  Did not trigger rule (probability not met)")
            return


class WorkingMemory:
    """A working memory containing all asserted facts."""

    def __init__(self, initial_facts):
        """Initialize a Role object."""
        self.facts = set()
        self._facts_by_first_character = {}  # Maps characters to facts beginning with that character (for efficiency)
        for fact in initial_facts:
            self.add_grounded_fact(fact=fact)

    def __str__(self):
        """Return string representation."""
        return "Working Memory"

    def __repr__(self):
        """Return string representation."""
        return self.__str__()

    def add_grounded_fact(self, fact):
        """Add the given grounded fact to the working memory."""
        if fact[0] == '*':
            raise Exception(f"Grounded fact includes the Kleene star: {fact}")
        self.facts.add(fact)
        try:
            self._facts_by_first_character[fact[0]].append(fact)
        except KeyError:
            self._facts_by_first_character[fact[0]] = [fact]

    def holds(self, condition, bindings):
        """Return whether the given precondition holds."""
        # Evaluate an "OR" expression, if applicable
        if condition.or_expression:
            for subcondition in condition.conditions:
                if self.holds(condition=subcondition, bindings=bindings):
                    if condition.negated:
                        return False
                    return True
            if condition.negated:
                return True
            return False
        # It's a normal condition, so evaluate it accordingly. First, use the bindings to ground the roles
        # in the precondition.
        ground_expression = condition.ground(bindings=bindings)
        # Compile the pool of candidate facts
        if ground_expression[0] != '*':
            facts_pool = self._facts_starting_with(character=ground_expression[0])
        else:
            facts_pool = self.facts
        if '*' in ground_expression:  # It uses the Kleene star, so treat it as a regex and match against all facts
            if ground_expression[0] == '*':
                ground_expression = "." + ground_expression
            pattern = re.compile(ground_expression)
        else:
            pattern = None
        for fact in facts_pool:
            match = (pattern and pattern.match(fact)) or ((not pattern) and ground_expression == fact)
            if match:
                if condition.negated:
                    return False
                return True
        if condition.negated:
            return True
        return False

    def _facts_starting_with(self, character):
        """Return all facts starting with the given character."""
        try:
            return self._facts_by_first_character[character]
        except KeyError:  # There's no facts yet with that first character
            return []

    def add(self, predicate, bindings):
        """Add a new fact into the working memory."""
        try:
            fact = ' '.join(e if type(e) is str else bindings[e.name].name for e in predicate.template)
        except KeyError:  # The predicate references an optional role that wasn't bound
            return
        if not fact.strip():
            return
        self.facts.add(fact)
        try:
            self._facts_by_first_character[fact[0]].append(fact)
        except KeyError:
            self._facts_by_first_character[fact[0]] = [fact]
        if config.VERBOSITY >= 2:
            print(utils.green(f"  {fact}"))

    def delete(self, predicate, bindings):
        """Delete a fact from the working memory, if it's present."""
        ground_expression = predicate.ground(bindings=bindings)
        for fact in list(self.facts):
            if fact == ground_expression:
                self.facts.remove(fact)
                self._facts_by_first_character[fact[0]].remove(fact)
                if config.VERBOSITY >= 2:
                    print(utils.red(f"  {fact}"))
                return

    def has_fact(self, fact):
        """Return whether the given fact is in the working memory."""
        return fact in self.facts


class Action:
    """An action that has occurred during rule execution."""

    def __init__(self, action_name, action_string, bindings):
        """Initialize an Action object."""
        self.name = action_name
        self.string = action_string
        self.bindings = bindings

    def __str__(self):
        """Return string representation."""
        return self.string

    def __repr__(self):
        """Return string representation."""
        return self.name

    @property
    def entities(self):
        """Return a list of all entities bound to roles for this action."""
        return list(self.bindings.values())
