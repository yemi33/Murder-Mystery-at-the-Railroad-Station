September 2020
James Ryan (jryan@carleton.edu)
--


This directory contains a number of text corpora. A "corpus" (plural: "corpora") is a collection of text items,
typically one in which the individual items all fall under a unified theme. For example, one of the corpora in
this directory contains 134 animal names ("animals.txt").

Text corpora are useful for text generation because we can randomly select items from a corpus to compose new instances
of generated text. For example, we can generate a sentence of the form "<NAME> is a beautiful <ANIMAL>!", where '<NAME>'
is filled in with a randomly selected name (from a corpus of names) and '<ANIMAL>' is filled in with a randomly
selected animal name (from a corpus of animal names).

Nearly all of these corpora come from Darius Kazemi's "corpora" repository on GitHub, which is available at
https://github.com/dariusk/corpora/tree/master/data. Darius is a leading voice in the Twitterbot community
who, like me, is interested in using computers to make weird computational artifacts.

In Darius's "corpora" repository, each corpus is formatted as a JSON file, which is a particular way of representing
structured data. While it's fairly easy to work with JSON in Python (using the "json" library:
https://docs.python.org/3/library/json.html), it's much easier to work with an even simpler format, where each
item in the corpus is placed on its own line in a text file. To make your life easier, I've converted several
corpora to this format and placed them in the "corpora" directory; take a look at 'animals.txt' to see what I mean.