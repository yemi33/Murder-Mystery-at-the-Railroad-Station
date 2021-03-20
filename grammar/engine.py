import random
import time


class GrammarEngine:
    """An engine for grammar-based text generation.

    Attributes:
        state:
            A dictionary mapping defined state variables to their values.
        rules:
            A list of ProductionRule objects, one for each production rule in the given grammar file.
        symbols:
            A list of NonterminalSymbol objects, one for each nonterminal symbol referenced anywhere
            in the given grammar file.
    """

    def __init__(self, file_path, initial_state=None, random_seed=None):
        """Initialize a GrammarEngine object.

        Args:
            file_path:
                A string containing the path to a grammar file in the expected format.
            initial_state:
                Optionally, a dictionary that will be stored as the initial engine state. This
                provides a means for preparing state variables ahead of time for use in
                your generated text. For instance, if you were generating text for a videogame,
                the initial_state could contain things like character names or aspects of the
                broader game state at any given point. If None is given, the state will be
                initialized to an empty dictionary.
            random_seed:
                Optionally, a value that will be used to seed the random module. If None is 
                passed, no seed will be used. Look up random seeds if you're not familiar 
                with the notion.

        Raises
            Exception:
                A value was passed for initial_state that was not None or a dictionary containing
                only str: str key-value pairs.
        """
        if initial_state is None:
            self.state = {}
        else:
            if type(initial_state) is not dict:
                raise Exception("initial_state must be either None or a dictionary.")
            for key, value in initial_state.items():
                if type(key) is not str:
                    raise Exception(f"Key '{key}' in initial_state is not a str.")
                if type(value) is not str:
                    raise Exception(f"Value '{value}' for key '{key}' in initial_state is not a str.")
                self.state = dict(initial_state)  # Create a copy to be safe
        self.symbols = []  # Gets populated with NonterminalSymbol objects
        self.rules = []  # Gets populated with ProductionRule objects
        self._parse_grammar_definition_file(file_path=file_path)
        self._validate_grammar()
        # If we received a random seed, use it to seed the random module
        if random_seed is not None:
            random.seed(random_seed)
        else:
            random.seed(time.time())  # Seed with the current UNIX time to introduce randomness

    def _parse_grammar_definition_file(self, file_path):
        """Parse the grammar definition file at the given file path.

        This method calls self._parse_rule_definition(), which updates self.symbols and self.rules via side effects,
        hence the lack of any return value here.

        Note: I use a leading underscore in this method name to cue that it is a private method, meaning that it
        should never be called except by this object's other instance methods. While some languages, like Java,
        require an explicit declaration of whether a method is private, in Python the leading underscore is just
        a convention that is meant to make the code more readable. Some IDEs, like PyCharm, will also issue a
        warning when a private method is called from outside its class. Finally, this docstring conforms to the
        Google Python Style Guide: https://github.com/google/styleguide/blob/gh-pages/pyguide.md#383-functions-
        and-methods. I don't always conform to this style guide, but in this case I do. One nice thing about using
        it for docstrings is that IDEs like PyCharm recognize the format and can use it to help you debug.

        Args:
            file_path:
                A string containing the path to a grammar definitions file in the expected format.

        Raises:
            IOError:
                An error occurred accessing the grammar definition file.
        """
        # Read in the raw grammar definition. If there's no file at this path, or if the path is otherwise
        # malformed, an IOError will be raised.
        grammar_definition = open(file_path).read()
        # Next, iterate over each line in the grammar definition to attempt to build a production rule for any line
        # that doesn't consists of non-whitespace characters or begin with '#' (our comment symbol).
        for line in grammar_definition.split('\n'):
            line = line.lstrip()  # Remove all leading whitespace on the line
            if not line:  # The line contained only whitespace, so now it's an empty string
                continue  # Move on to the next iteration of the 'for' loop, i.e., to the next line
            if line.startswith('#'):  # It's a comment
                continue
            while '\t\t' in line:  # Replace consecutive tab characters with a single tab character
                line = line.replace('\t\t', '\t')
            # If we get to here, this must be a rule definition, though it may be malformed. Here, we'll use
            # a try-except block to safely attempt to parse it as if it were in the expected format. If it's
            # not in the expected format, i.e., it doesn't have two fields separated by a single tab, a
            # ValueError will be raised indicating that splitting on the tab character did not produce exactly
            # two components. If this happens, we'll raise an Exception with an error message including the
            # malformed rule definition.
            try:
                rule_head, rule_bodies_str = line.split('->')
            except ValueError:
                # Let's form a nice error message that includes the exact rule definition that was malformed. We'll
                # do this using a Python f-String (http://zetcode.com/python/fstring/).
                if '->' not in line:
                    error_message = f"Malformed rule definition (no '->' delimiter): '{line}'"
                else:  # It has too few or too many components; there should be exactly two: name and values
                    error_message = f"Malformed rule definition: '{line}'"
                raise Exception(error_message)
            # Next, make sure that the rule bodies contain a balance between opening and closing angle brackets
            if rule_bodies_str.count('<') != rule_bodies_str.count('>'):
                raise Exception(f"Rule definition has mismatched angle brackets: {line}")
            # At this point, there's two ways that this rule definition could be malformed: 1) the rule head is an
            # empty string or comprises only whitespace, or 2) the rule-bodies component is an empty string or
            # comprises only whitespace. We'll check for both and raise an Exception, with an informative error
            # message, in each case.
            rule_head = rule_head.strip()  # Remove leading or trailing whitespace
            rule_bodies_str = rule_bodies_str.strip()
            if not rule_head:  # It comprised only whitespace
                error_message = f"Rule definition includes no rule head: {line}"
                raise Exception(error_message)
            if not rule_bodies_str:  # It comprised only whitespace
                error_message = f"Rule definition includes no rule bodies: {line}"
                raise Exception(error_message)
            # If we got to here, we successfully parsed out the rule head and rule bodies. Next, we'll parse the
            # list of bodies; this is simply a comma separated list. Note that calling str.split(delimiter) on a
            # string that doesn't include the delimiter is just fine -- it will just return the entire string.
            raw_rule_bodies = rule_bodies_str.split('|')
            # Some of these values may be commands to load in the contents of a corpus file, so let's iterate
            # over them one by one to check. If we find a corpus reference, we'll remove that from the rule bodies
            # and add to that collection every element in the referenced corpus.
            rule_bodies = []
            for raw_rule_body in raw_rule_bodies:
                if not raw_rule_body.startswith('$'):
                    # It's a regular rule body, so append it to the list of rule bodies and move onto the
                    # next iteration of the loop.
                    rule_bodies.append(raw_rule_body)
                    continue
                corpus_filename = raw_rule_body[1:]  # Remove the leading dollar sign
                corpus_values = self._load_corpus(corpus_filename=corpus_filename)
                rule_bodies += corpus_values
            # Now go through and parse each rule body, which will cause us to instantiate NonterminalSymbol objects
            # (for the rule heads) and ProductionRule objects, as needed.
            for rule_body in rule_bodies:
                self._parse_rule_definition(rule_head_name=rule_head, rule_body_str=rule_body, raw_definition=line)

    def _validate_grammar(self):
        """Verify that there are no nonterminal symbols in this grammar that lack production rules.

        Raises:
            Exception:
                At least one nonterminal symbol in the grammar has no production rules.
        """
        for nonterminal_symbol in self.symbols:
            if not nonterminal_symbol.rules:
                error_message = "The following nonterminal symbol has no "
                error_message += f"production rules: '{nonterminal_symbol.name}'."
                raise Exception(error_message)

    @staticmethod
    def _load_corpus(corpus_filename):
        """Return the contents of a corpus loaded from a corpus file.

        Note: I use the decorator '@staticmethod' because this instance method does not require access to
        the instance's data, i.e., there is no point to passing the 'self' argument, since it's not used
        anywhere in the method. While Python has formal support for 'static' methods like this one, I'm
        using here as a convention that makes the code easier to understand; for example, by using the
        decorator, I express to you that this method will not -- and, in fact, cannot -- modify the object
        instance's attributes via side effects.

        Args:
            corpus_filename:
                The filename for the corpus that's to be loaded.

        Returns:
            A list of strings.

        Raises:
            IOError:
                There is no corpus file with the given name in the 'corpora' folder.
        """
        return open(f"grammar/corpora/{corpus_filename}").read().split('\n')

    def _parse_rule_definition(self, rule_head_name, rule_body_str, raw_definition):
        """Parse the given rule definition.

        This method calls updates self.symbols and self.rules via side effects, hence the lack of any return value.

        Args:
            rule_head_name:
                A string, being the name of the nonterminal symbol that serves as a rule head in this rule definition.
            rule_body_str:
                The body of this production rule, expressed as a string (e.g., "<DET> <NOUN> <VERB>.").
        """
        # First, retrieve the NonterminalSymbol object associated with the rule head. If one has not already
        # been instantiated, we'll create it now.
        rule_head_object = self._get_symbol(nonterminal_symbol_name=rule_head_name, create_if_undefined=True)
        # This list, representing the rule body, will be populated with strings (terminal symbols) and
        # NonterminalSymbol objects (symbol references) and VariableReference objects (variable references).
        rule_body = []
        # Iterate over the rule definition, one character at a time, looking specifically for the angle
        # brackets that demarcate symbol references and state-variable references.
        iterating_over_reference = False
        referenced_symbol_name = None
        terminal_symbol = ''
        for character in rule_body_str:
            if iterating_over_reference:
                if character != '>':  # We're still iterating over a reference, so append this character
                    referenced_symbol_name += character
                else:  # We've hit the end of the reference...
                    iterating_over_reference = False
                    # Check if the reference includes a write-state directive (e.g., "<NAME @hero_name>") or
                    # a state-variable reference (e.g., "<@hero_name>")
                    try:
                        referenced_symbol_name, variable_name = referenced_symbol_name.split('@')
                    except ValueError:
                        variable_name = None
                    referenced_symbol_name = referenced_symbol_name.strip()  # Strip off any whitespace
                    if not referenced_symbol_name:
                        # This is a state-variable reference
                        variable_reference_object = VariableReference(name=variable_name)
                        rule_body.append(variable_reference_object)
                    else:
                        symbol_object = self._get_symbol(
                            nonterminal_symbol_name=referenced_symbol_name,
                            create_if_undefined=True,
                        )
                        if variable_name:
                            rule_body.append((symbol_object, f"@{variable_name}"))
                        else:
                            rule_body.append(symbol_object)
            elif character == '<':  # We've hit the beginning of a symbol reference
                # If there was a terminal symbol preceding this symbol reference, append it to the rule body
                if terminal_symbol:
                    rule_body.append(terminal_symbol)
                    terminal_symbol = ''
                iterating_over_reference = True
                referenced_symbol_name = ''
            else:  # We must be iterating over a terminal symbol
                terminal_symbol += character
        # Even though we're done iterating over the rule definition, there may have been a terminal symbol
        # at the end of it, which we would have failed to have added to the body. Let's make sure to do
        # that here.
        if terminal_symbol:
            rule_body.append(terminal_symbol)
        # Finally, instantiate a ProductionRule object and append it to the list of rules
        production_rule_object = ProductionRule(head=rule_head_object, body=rule_body, raw_definition=raw_definition)
        self.rules.append(production_rule_object)

    def _get_symbol(self, nonterminal_symbol_name, create_if_undefined=False):
        """Return the NonterminalSymbol object for the symbol with the given name, if any, otherwise None.

        Args:
            nonterminal_symbol_name:
                A string, being the name of the nonterminal symbol that is to be returned.
            create_if_undefined:
                If True and there is no defined symbol with the given name, a new one with that name
                will be created and returned.
        Returns:
            A NonterminalSymbol object, if one by the given name is defined by the end of the procedure, else None.
        """
        for nonterminal_symbol in self.symbols:
            if nonterminal_symbol.name == nonterminal_symbol_name:
                return nonterminal_symbol
        if create_if_undefined:
            new_symbol = NonterminalSymbol(name=nonterminal_symbol_name)
            self.symbols.append(new_symbol)
            return new_symbol
        return None

    def generate(self, start_symbol_name, outfile_path=None, debug=False):
        """Use the grammar, starting from the given nonterminal symbol, to generate single text output.

        Args:
            start_symbol_name:
                A string, being the name of the nonterminal symbol that will be used as the start symbol for this
                generation attempt.
            outfile_path:
                If any, a string containing the path to which the output will be written as a file.
            debug:
                If True, each step in the intermediate derivation will be printed out to the console.

        Returns:
            A string, being a single text output produced by recursively rewriting the start symbol using the grammar.

        Raises:
            Exception:
                A reference to an undefined state variable was encountered.
        """
        # First, we need to retrieve the NonterminalSymbol object associated with this name. If there isn't one, we'll
        # elect to raise an Exception to let the caller know.
        start_symbol_object = self._get_symbol(nonterminal_symbol_name=start_symbol_name)
        if not start_symbol_object:  # There is no defined nonterminal symbol by that name, so raise an Exception
            error_message = f"There is no defined nonterminal symbol with the name {start_symbol_name}. "
            all_defined_symbol_names = ", ".join(sorted(symbol.name for symbol in self.symbols))
            error_message += f"These nonterminal symbols are defined: {all_defined_symbol_names}."
            raise Exception(error_message)
        # If we retrieved start symbol, use it to generate text. This process begins by randomly selecting a production
        # rule of the start symbol, which we execute to rewrite the start symbol as a sequence of nonterminal symbols
        # and terminal symbols -- i.e., we rewrite the symbol to be the body of the rule we executed. We call this
        # result the "intermediate derivation." From here, we iteratively carry out this process over and over, each
        # time rewriting the first nonterminal symbol (moving from left to right) in the intermediate derivation. Once
        # there's only terminal symbols in the intermediate derivation, we have our generated text, and we return that.
        if debug:
            self.inspect_state()
            print(start_symbol_object)
        intermediate_derivation = [start_symbol_object]
        while self._derivation_includes_reference(derivation=intermediate_derivation):
            # Replace the next nonterminal symbol in the intermediate derivation with the body of one of its rules
            for i, element in enumerate(intermediate_derivation):
                if isinstance(element, NonterminalSymbol):
                    intermediate_derivation = (
                        intermediate_derivation[:i] + element.rewrite() + intermediate_derivation[i+1:]
                    )
                    if debug:
                        print(f"\n{self._render_surface_form(derivation=intermediate_derivation)}")
                    break  # Loop back over the intermediate derivation, starting again from the left
                if isinstance(element, VariableReference):
                    try:
                        resolved_variable = self.state[element.name]
                    except KeyError:
                        # We've encountered a reference to an undefined variable, so let's throw an exception.
                        error_message = f"Encountered undefined state variable: '{element.name}'"
                        raise Exception(error_message)
                    intermediate_derivation = (
                        intermediate_derivation[:i] + [resolved_variable] + intermediate_derivation[i + 1:]
                    )
                    if debug:
                        print(f"\n{self._render_surface_form(derivation=intermediate_derivation)}")
                    break
                if isinstance(element, tuple):
                    symbol, variable_to_write_to = element
                    # We have encountered a write-state declaration
                    intermediate_derivation = (
                        intermediate_derivation[:i] +
                        [f"<$$begin {variable_to_write_to}>"] +
                        symbol.rewrite() +
                        [f"<$$end {variable_to_write_to}>"] +
                        intermediate_derivation[i + 1:]
                    )
                    if debug:
                        print(f"\n{self._render_surface_form(derivation=intermediate_derivation)}")
                    break
                if element.startswith('<$$end'):
                    # We can now write to the state the terminal results of recursively rewriting a nonterminal
                    # symbol associated with a state-write declaration.
                    variable_name = element.split()[1][1:-1]
                    value_to_write = ''
                    reached_value_start = False
                    for _element in intermediate_derivation:
                        if _element == f"<$$begin @{variable_name}>":
                            reached_value_start = True
                        elif _element == f"<$$end @{variable_name}>":
                            # We've reached the end of the value, so write it to the state
                            self.set_state(variable_name=variable_name, value=value_to_write, debug=debug)
                            break
                        elif reached_value_start:
                            value_to_write += _element
                    # Remove the "<$$begin @var>" and "<$$end @var>" markers
                    for j, _element in enumerate(intermediate_derivation):
                        if _element == f"<$$begin @{variable_name}>":
                            intermediate_derivation[j] = ''
                        elif _element == f"<$$end @{variable_name}>":
                            intermediate_derivation[j] = ''
                    break
        # Once we get to here, the intermediate derivation is composed entirely of terminal symbols (i.e., strings),
        # so we can just join them together into our text output, which we then return.
        if debug:
            self.inspect_state()
        output = self._render_surface_form(derivation=intermediate_derivation)
        if outfile_path:
            with open(outfile_path, 'w') as outfile:
                outfile.write(output)
        return output

    @staticmethod
    def _derivation_includes_reference(derivation):
        """Return whether the given derivation includes an unresolved reference (meaning derivation is incomplete).

        Args:
            derivation:
                A list of references and/or terminal symbols (i.e., strings). Some of the references may
                be expressed as tuples of the form (NonterminalSymbol object, variable to write).

        Returns:
            True if the derivation includes at least one NonterminalSymbol, else False.
        """
        for element in derivation:
            if isinstance(element, NonterminalSymbol):
                return True
            if isinstance(element, VariableReference):
                return True
            if isinstance(element, tuple):
                return True  # Any tuple in the derivation will always include a NonterminalSymbol
            if element.startswith('<$$'):
                return True
        return False

    @staticmethod
    def _render_surface_form(derivation):
        """Return a string representation of the given intermediate derivation.

        Args:
            derivation:
                A list of references and/or terminal symbols (i.e., strings). Some of the references may
                be expressed as tuples of the form (NonterminalSymbol object, variable to write).

        Returns:
            A string, representing the surface form of this derivation. If there are still unresolved references
            in the derivation, these will be included in the surface form.
        """
        rendering = ''
        for element in derivation:
            if isinstance(element, NonterminalSymbol):
                rendering += str(element)
            elif isinstance(element, VariableReference):
                rendering += str(element)
            elif isinstance(element, tuple):
                symbol, variable_reference = element
                rendering += f"<{symbol.name} {variable_reference}>"
            else:
                if element.startswith('<$$'):
                    continue
                # Terminal symbol
                rendering += element
        return rendering

    def set_state(self, variable_name, value, debug=False):
        """Bind the given variable name to the given value."""
        self.state[variable_name] = value
        if debug:
            print(f"\n\tSet variable '{variable_name}' to '{value}'")

    def inspect_state(self):
        """Pretty-print the contents of the engine state."""
        if not self.state:
              print(f"\n{'-'*20}\nEngine State: (empty)")
              print("-"*20 + '\n')
        else:  
            print(f"{'-'*20}\nEngine State:")
            for key, value in self.state.items():
                print(f"\n\t * {key}: {value}")
            print("-"*20 + '\n')

    def clear_state(self):
       """Clear the current engine state."""
       self.state = {}

    def export_state(self):
       """Return a copy of the current engine state."""
       state_copy = dict(self.state)
       return state_copy


class NonterminalSymbol:
    """A nonterminal symbol in a generative grammar.

    Attributes:
        name:
            A string, being the symbol's name.
    """

    def __init__(self, name):
        """Initialize a NonterminalSymbol object.

        Args:
            name:
                A string representing the symbol name.
        """
        self.name = name
        self.rules = []  # Gets populated with ProductionRule objects

    def __str__(self):
        """Return string representation."""
        return f"<{self.name}>"

    def __repr__(self):
        """Return string representation."""
        return self.__str__()

    def rewrite(self):
        """Rewrite this symbol using one of its production rules.

        This method rewrites any reference to this symbol (in a production rule) by randomly selecting, and
        executing, one of its production rules. Of course, we could modify this method to implement a different
        policy, such as using each rule once, with no repeating until every rule has been used once, and so on.

        Returns:
            The rule body of the selected rule, in the form of a list of NonterminalSymbol objects and
            strings (i.e., terminal symbols).
        """
        production_rule_to_execute = random.choice(self.rules)
        return production_rule_to_execute.body


class ProductionRule:
    """A production rule in a generative grammar.

    Attributes:
        head:
            A NonterminalSymbol object, being the head of this production rule.
        body:
            A list of NonterminalSymbol objects and strings (i.e., terminal symbols).
        raw_definition:
            The raw definition of this production rule, as found in the grammar definition file (useful for debugging).
    """

    def __init__(self, head, body, raw_definition):
        """Initialize a ProductionRule object.

        Args:
            head:
                A NonterminalSymbol object, being the head of this production rule.
            body:
                A list of NonterminalSymbol objects and strings (i.e., terminal symbols).
        """
        self.head = head
        self.body = body
        self.raw_definition = raw_definition
        self.head.rules.append(self)

    def __str__(self):
        """Return string representation."""
        return self.raw_definition

    def __repr__(self):
        """Return string representation."""
        return self.__str__()


class VariableReference:
    """A reference to a state variable, included in the body of a production rule.

    Attributes:
        name:
            The name of the state variable.
    """

    def __init__(self, name):
        """Initialize a VariableReference object.

        Args:
            name:
                The name of the variable being referenced.
        """
        self.name = name

    def __str__(self):
        """Return string representation."""
        return f"<@{self.name}>"

    def __repr__(self):
        """Return string representation."""
        return self.__str__()
