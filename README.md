## Description

**Chunklate** checks png images for file format corruption and fix them .

Currently **Chunklate** is in beta and able to provide those features:

- Provide all informations it could get from a png file
- Repair Magic Header and Footer
- Repair wrong chunk length  
- Repair wrong chunk name
- Repair wrong chunk crc
- Repair line feed conversion
- Save each modifications in a different file
- Provide a summary of all modifications 
- User friendly human readability
- Bruteforce corrupted data chunk (Work in progress)
- Repair wrong image size (Todo)
- Repair missplaced chunks (Todo)
- Replace critical missing chunk (Todo)



## Usage

>usage: Chunklate.py [-h] [-f FILE]
>
>optional arguments:
>  -h, --help            show this help message and exit
>  -f FILE, --file FILE  File path.
