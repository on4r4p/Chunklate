![Alt Text](https://github.com/on4r4p/Chunklate/blob/ctf/Chunklate.gif)

## Description

**Chunklate** checks png images for file format corruption and fix them .

##### Work in progress

**Chunklate**'s aim is to be able to provide those features:

- Get all informations it could find from a png file
- Repair Magic Header and Footer
- Repair wrong chunk length  
- Repair wrong chunk name
- Repair wrong chunk crc
- Repair wrong image size
- Repair line feed conversion
- Smart crc fixer based on errors found
- Save each modifications in a different file
- Provide a summary of all modifications 
- User friendly human readability
- Bruteforce corrupted data chunk
- Repair missplaced chunks (Just IHDR for now)
- Replace critical missing chunk (Todo)



## Usage

    usage: Chunklate.py [-h] [-f FILE] [-c] [-p] [-d] [-dp] [-ep] [-sp] [-stfu] [-a]
    
    optional arguments:
      -h, --help            show this help message and exit
      -f FILE, --file FILE  File path.
      -c, --clear           Clear screen at each saves.
      -p, --pause           Pause at each saves.
	  -d, --debug           Debug stuffs.
	  -dp, --pause-debug    Pause at Debug stuffs.
	  -ep, --pause-error    Pause at errors.
	  -sp, --pause-dialogue Pause at dialogues.
	  -stfu, --shut-the-fuck-up Show minimal output.
	  -a, --auto            Auto Choose action.
