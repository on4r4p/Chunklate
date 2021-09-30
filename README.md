## Description

**Chunklate** checks png images for file format corruption and fix them .

Currently **Chunklate** is able to provide those features:

- Provide all informations it could get from a png file (Work in progress)
- Repair Magic Header and Footer
- Repair wrong chunk length  
- Repair wrong chunk name
- Repair wrong chunk crc
- Save each modifications in a different file
- Repair line feed convertion (Todo)
- Repair wrong image size (Todo)
- Repair missplaced chunks (Todo)
- Replace critical missing chunk (Todo)
- User friendly candy eye (Work in progress)
- Provide a summary of all modifications (Todo)

## Usage

>usage: Chunklate.py [-h] [-f FILE]
>
>optional arguments:
>  -h, --help            show this help message and exit
>  -f FILE, --file FILE  File path.
