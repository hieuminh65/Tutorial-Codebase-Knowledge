# Fixxed

- add try catch to debug azure function deployment error, as azure function deployment error are not display in the azure function log
- change the log dir to /tmp
- remove git clone from crawl github files .py
- install the requirements in the requirements.txt
- remove function.json to avoid mixing with python programming model V2 of azure function

# Unexpected behavior

- Sometime the function work, sometimes it crashes at picking up the job from the queue
