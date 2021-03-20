import time
import random
from grammar.engine import GrammarEngine
from rule_system.engine import RuleEngine
from book.pdf_gen import PDF

def mystery():
  
  #create a book
  book = PDF(
        filename=f"generated_books/c3_murder_book_{int(time.time())}.pdf",
        width=8.5,
        height=5.5,
        x_margin=1.0,
        y_margin=1.0,
        initial_base_style="BodyText",
        initial_font_name="Courier",
        initial_font_size=16,
        initial_font_color="black"
  )

  #set initial style
  book.style(leading=30, space_between_paragraphs=10, background_padding=20)
  
  #prepare rule engine
  rule_engine = RuleEngine(
        path_to_domain_file='rule_system/content/mystery_domain.txt',
        path_to_rules_file='rule_system/content/mystery_rules.txt',
        shuffle_randomly=True,
        random_seed=None
  )

  #execute rule systems
  while not rule_engine.produced_action(action_name='Briefing'):
    rule_engine.execute(n=1)

  #choose protagonist(s)
  detective = None
  for entity in rule_engine.entities:
    detective_fact = f"{entity.name} is a detective"
    if rule_engine.working_memory.has_fact(fact=detective_fact):
      detective = entity
      break
  else:
      raise Exception("Could not find detective")
  
  murderer = None
  for entity in rule_engine.entities:
    murderer_fact = f"{entity.name} is the culprit"
    if rule_engine.working_memory.has_fact(fact=murderer_fact):
      murderer = entity
      break
  else:
      raise Exception("Could not find detective")
  
  victim = None
  for entity in rule_engine.entities:
    victim_fact = f"{entity.name} is the victim"
    if rule_engine.working_memory.has_fact(fact=victim_fact):
      victim = entity
      break
  else:
      raise Exception("Could not find detective")

  print(detective, murderer, victim)

  #insert title page
  book.insert_title_page(title=f"The Murder at the Railroad Station", author="Ben Preiss and Yemi Shin", alignment="center")
  
  #select plot
  plot=rule_engine.actions_involving(murderer.name)
  plot+=rule_engine.actions_involving(victim.name)
  plot+=rule_engine.actions_involving(detective.name)

  print(plot)

  #prepare grammar engine
  grammar_engine = GrammarEngine(
        file_path='grammar/grammars/mystery_grammar.txt',
        initial_state=None,
        random_seed=None
  )

  #intro
  '''
  intro = grammar_engine.generate(start_symbol_name="MainCharacterIntro")
  book.insert_space(height=1.0)
  book.style(alignment="center")
  book.write(text=intro)
  '''
    
  #write the content of the story
  for i, action in enumerate(plot):
      for role_name, entity in action.bindings.items():
        entity.add_to_grammar_engine_state(
            grammar_engine=grammar_engine,
            variable_name=role_name
        )

      text = grammar_engine.generate(start_symbol_name=action.name, debug=False)
      #print(text);
      #book.write(text=text)
        
      book.style(
        font_color="black",
        alignment="left",
        background_color="white"
      )
      book.insert_page_break()
      book.insert_space(height=1.0)
      book.write(text=text)
      book.insert_page_break()
  
  #customizing text for specific actions
  '''
  if rule_engine.working_memory.has_fact(fact=f"{protagonist.name} dislikes Bob"):
      text = f"Oh my: {protagonist.name} dislikes Bob!"
  else:
      text = f"{protagonist.name} doesn't NOT like Bob..."
  '''
  
  book.insert_page_break()

  #change style
  book.style(background_color="black", font_color="white")
  book.insert_space(height=1.0)

  #write content of story into book 
  book.write(text=text)
  
  book.insert_page_break()

  #change style
  book.style(
      alignment="center",
      font_color="black",
      background_color="white",
      space_between_paragraphs=10,
      leading=5
  )

  #write facts in appendix
  book.write("Appendix: Facts")
  book.insert_space(height=1.0)
  book.style(font_name="Courier-Oblique", font_size=10, alignment="left", space_between_paragraphs = 2)
  for fact in sorted(rule_engine.working_memory.facts):
      book.write(f"  {fact}")
    
  #insert image
  book.insert_page_break()
  book.insert_image(filename="book/images/james.png", width=1.5)
    
  #build the pdf
  book.build(page_numbers=True)

def run():
    """The function James will be using to grade your component."""
    print("\n\n-- Component 3 -- ")
    mystery()
