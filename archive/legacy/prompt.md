use tavoli and research the drawings with python 

https://docs.google.com/drawings/d/1eSvF7_ekvOWy1q0npqI8f37J9IARPBOZJte5Q3pDspw/edit 

i want to create an easy way for teachers to create drawings or figures in the correct style
these drawings can be figures examples simplifications graphs etc
style includes things like, colors, font, line graph or error styling, simplification level of real things


i want to create a website with a toolbox for teachers to easily do this having a nice interface

my goal is to find a method to do this 

to do this we first need to describe all different figure types and systems really objectively

define the exact colors etc

we currently create these figures in google drawings
but we want to be able to generate these drawings with ai 

for that we need to teach and describe how a model should generate the text to create these drawings
this generation will be able to be done with 
python or raw text or with other things, like latex compilers etc as long as it is in the Leerlevels style

to train a model to choose how it is going to generate the drawings and the final output target we need to know how it is currently stored and saved
svg's of drawings are not sufficient because they are  not easily imported to google drawings, we want the teachers to be able to edit everything there as well, like they are used to 

so you first task is to emulate a user and try to load and edit and save a google drawing
please research online to find how this is done  and how we should do this
i have loaded a few drawingereferences in the file system, please do not try to read them
here is the one you should try to decode
https://docs.google.com/drawings/d/1eSvF7_ekvOWy1q0npqI8f37J9IARPBOZJte5Q3pDspw/edit
and generate the svg or edit