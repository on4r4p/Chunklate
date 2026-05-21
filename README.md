![Alt Text](https://github.com/on4r4p/Chunklate/blob/ctf/Chunklate.gif)

## Description

**Chunklate** checks png images for file format corruption and fix them .

##### Work in progress May Not Work as Expected ATM !

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
- Replace critical missing chunk



## Usage

Install the runtime dependencies in a virtual environment:

    ./scripts/bootstrap_dev.sh
    . .venv/bin/activate

Run Chunklate on a PNG file:

    chunklate -f path/to/file.png

Or run it directly from the repository:

    python Chunklate.py -f path/to/file.png

Current CLI:

    usage: Chunklate.py [-h] [-f FILE] [-c] [-p] [-d] [-dp] [-ep] [-sp] [-stfu] [-a]
                       [--output-dir DIR] [--max-saves N]

    optional arguments:
      -h, --help            show this help message and exit
      -f FILE, --file FILE  File path.
      -c, --CLEAR, --clear  CLEAR screen at each saves.
      -p, --pause           Pause at each saves.
      -d, --debug           Debug stuffs.
      -dp, --pause-debug    Pause at Debug stuffs.
      -ep, --pause-error    Pause at errors.
      -sp, --pause-dialogue Pause at dialogues.
      -stfu, --shut-the-fuck-up Show minimal output.
      -a, --auto            Auto Choose action.
      --output-dir DIR      Directory where Folder_* repair outputs are written.
      --max-saves N         Exit successfully after writing N repaired files.

## Development

Install or refresh all runtime and development dependencies:

    ./scripts/bootstrap_dev.sh

Run the smoke tests:

    .venv/bin/python -m pytest

Run only the repair regression tests:

    .venv/bin/python -m pytest tests/test_repairs.py

Or without pytest:

    ./tests/test_cli.py
    ./tests/test_png.py
    ./tests/test_relics_state.py
    ./tests/test_repairs.py
