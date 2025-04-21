# Termo Solver and Game Project

## Description

This project provides tools related to the Brazilian Portuguese word game **Termo** (similar to Wordle).

It contains:
1.  A script to process and prepare a valid 5-letter word list (`process_word_list.py`).
2.  A playable command-line version of the Termo game (`TermoGame.py`) that uses the generated word list.
3.  *(Future Work)* A Termo solver script.

## Components

### 1. Word List Processor (`process_word_list.py`)

This script performs the necessary initial processing on a raw list of Portuguese words. Its tasks are:

* Read an input file named `palavras.txt` (expected to contain one Portuguese word per line, UTF-8 encoded).
* Filter out words that do not have exactly 5 letters.
* Convert all 5-letter words to lowercase.
* Remove accents from the words (e.g., "café" becomes "cafe").
* Remove any duplicate words after processing.
* Write the resulting unique, 5-letter, accent-free words to a new file named `palavras_5letras.txt`, sorted alphabetically.

This cleaned file, `palavras_5letras.txt`, provides the valid word list required for the game and the future solver.

### 2. Termo Game (`TermoGame.py`)

This script allows you to play a command-line version of Termo.

* It uses the cleaned word list (`palavras_5letras.txt`).
* It chooses a secret 5-letter word.
* You have 6 attempts to guess the word.
* It provides feedback using colors or symbols (⬜🟨🟩) for each guess.

## How to Use

### Preparing the Word List

1.  Ensure you have a raw Portuguese word list file named `palavras.txt` (UTF-8 encoded) in the project directory.
2.  Run the processing script:
    ```bash
    python process_word_list.py
    ```
3.  This will generate the `palavras_5letras.txt` file needed for the game.

### Playing the Game

![Captura de tela 2025-04-13 144036](https://github.com/user-attachments/assets/4526f296-4b8d-4eb6-af65-bd2a265f1ea9)

1.  Make sure the `palavras_5letras.txt` file exists in the same directory as `TermoGame.py`. (Run the processor script first if needed).
2.  Run the game script from your terminal:
    ```bash
    python TermoGame.py
    ```
3.  Follow the on-screen instructions to play.

### Solver

![image](https://github.com/user-attachments/assets/15529c74-5926-4b33-8ae9-941a28d76ec6)

## Prerequisites

* Python 3
* For `process_word_list.py`: A raw Portuguese word list file named `palavras.txt` (UTF-8 encoded).

## Future Work: The Solver

* Improve solver solution
