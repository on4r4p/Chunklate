![Alt Text](https://github.com/on4r4p/Chunklate/blob/ctf/Chunklate.gif)

## Description

**Chunklate** checks png images for file format corruption and fix them .

##### Work in progress - Not fully working

**Chunklate**'s aim is to be able to provide those features:

- Get all informations it could find from a png file
- Repair Magic Header and Footer
- Repair wrong chunk length  
- Repair wrong chunk name
- Repair wrong chunk crc
- Repair line feed conversion
- Save each modifications in a different file
- Provide a summary of all modifications 
- User friendly human readability
- Smart crc fixer based on errors found(Work in progress)
- Bruteforce corrupted data chunk (Todo)
- Repair wrong image size (Todo)
- Repair missplaced chunks (Todo)
- Replace critical missing chunk (Todo)



## Usage

    usage: Chunklate.py [-h] [-f FILE] [-c] [-p] [-d] [-a]
    
    optional arguments:
      -h, --help            show this help message and exit
      -f FILE, --file FILE  File path.
      -c, --clear           Clear screen at each saves.
      -p, --pause           Pause at each saves.
	  -d, --debug           Debug stuffs.
	  -a, --auto            Auto Choose action.
