import random
import unicodedata
import os
import sys
from ortools.sat.python import cp_model 

WORD_LIST_FILE = 'palavras_5letras.txt'

WORD_LENGTH = 5
MAX_ATTEMPTS = 6


USE_COLORS = True # Change to False if you cannot see the colors

if USE_COLORS:
    COLOR_GREEN = '\033[92m'
    COLOR_YELLOW = '\033[93m'
    COLOR_GRAY = '\033[90m'
    COLOR_RESET = '\033[0m'
    LETTER_ABSENT_FORMAT = COLOR_GRAY + '{}' + COLOR_RESET
    LETTER_WRONG_POS_FORMAT = COLOR_YELLOW + '{}' + COLOR_RESET
    LETTER_CORRECT_POS_FORMAT = COLOR_GREEN + '{}' + COLOR_RESET
else:
    SYMBOL_ABSENT = '⬜'
    SYMBOL_WRONG_POS = '🟨'
    SYMBOL_CORRECT_POS = '🟩'
    LETTER_ABSENT_FORMAT = SYMBOL_ABSENT + ' {}'
    LETTER_WRONG_POS_FORMAT = SYMBOL_WRONG_POS + ' {}'
    LETTER_CORRECT_POS_FORMAT = SYMBOL_CORRECT_POS + ' {}'


def remove_accents(text):
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def load_words(filepath):
    if not os.path.exists(filepath):
        print(f"Fatal Error: Word file '{filepath}' not found.")
        sys.exit(1)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            words = [remove_accents(line.strip().lower())
                     for line in f if len(line.strip()) == WORD_LENGTH]
        valid_words = set(words)
        if not valid_words:
             print(f"Error: No valid {WORD_LENGTH}-letter words found in '{filepath}'.")
             sys.exit(1)
        print(f"{len(valid_words)} {WORD_LENGTH}-letter words loaded from '{filepath}'.")
        return valid_words
    except Exception as e:
        print(f"Error reading word file '{filepath}': {e}")
        sys.exit(1)

def choose_secret_word(valid_words):
    if not valid_words:
        return None
    return random.choice(list(valid_words))

#Compares the guess with the secret word and generates feedback.
#
#Returns:
#tuple: (visual_feedback_str, is_correct, structured_feedback_list)
#    visual_feedback_str (str): Formatted string with colors/symbols.
#    is_correct (bool): True if the guess is correct.
#    structured_feedback_list (list): List of tuples  where status is 'correct', 'present', or 'absent'.

def check_guess(guess, secret_word):
    if len(guess) != WORD_LENGTH or len(secret_word) != WORD_LENGTH:
        return "Internal error: Invalid length", False, []

    visual_feedback = [''] * WORD_LENGTH
    structured_feedback = [None] * WORD_LENGTH
    is_correct = (guess == secret_word)

    if is_correct:
        for i in range(WORD_LENGTH):
            visual_feedback[i] = LETTER_CORRECT_POS_FORMAT.format(guess[i].upper())
            structured_feedback[i] = (guess[i], 'correct', i)
        return " ".join(visual_feedback), True, structured_feedback

    secret_letter_counts = {}
    for letter in secret_word:
        secret_letter_counts[letter] = secret_letter_counts.get(letter, 0) + 1

    for i in range(WORD_LENGTH):
        guess_letter = guess[i]
        if guess_letter == secret_word[i]:
            visual_feedback[i] = LETTER_CORRECT_POS_FORMAT.format(guess_letter.upper())
            structured_feedback[i] = (guess_letter, 'correct', i)
            secret_letter_counts[guess_letter] -= 1

    for i in range(WORD_LENGTH):
        if visual_feedback[i] == '':
            guess_letter = guess[i]
            if guess_letter in secret_letter_counts and secret_letter_counts[guess_letter] > 0:
                visual_feedback[i] = LETTER_WRONG_POS_FORMAT.format(guess_letter.upper())
                structured_feedback[i] = (guess_letter, 'present', i)
                secret_letter_counts[guess_letter] -= 1
            else:
                visual_feedback[i] = LETTER_ABSENT_FORMAT.format(guess_letter.upper())
                # Check if the letter is truly absent 
                is_truly_absent = True
                for j in range(WORD_LENGTH):
                     # If the same letter was marked as correct or present elsewhere, it's not totally absent
                     if structured_feedback[j] and structured_feedback[j][0] == guess_letter and structured_feedback[j][1] != 'absent':
                          break
                structured_feedback[i] = (guess_letter, 'absent', i)


    return " ".join(visual_feedback), False, structured_feedback

class TermoSolverCSP:
    def __init__(self, valid_words, word_length):
        self.all_valid_words = valid_words.copy() # Keep the original list
        self.possible_words = valid_words.copy()
        self.word_length = word_length
        self.guesses_history = []
        self.feedback_history = [] # List of structured_feedback

        # Accumulated constraints
        self.green_letters = {} # {index: letter}
        self.yellow_letters = {} # {index: set(letters)} - Letters present but in the wrong spot
        self.gray_letters = set() # set(letters) - Definitely absent letters
        self.min_letter_counts = {} # Minimum letter count based on green/yellow feedback

    # Updates internal constraints based on the latest feedback
    def _update_constraints(self, guess, structured_feedback):
        current_guess_counts = {}
        for letter in guess:
            current_guess_counts[letter] = current_guess_counts.get(letter, 0) + 1

        current_positive_counts = {}

        for letter, status, index in structured_feedback:
            if status == 'correct':
                self.green_letters[index] = letter
                if index in self.yellow_letters:
                    self.yellow_letters[index].discard(letter)
                current_positive_counts[letter] = current_positive_counts.get(letter, 0) + 1

            elif status == 'present':
                if index not in self.yellow_letters:
                    self.yellow_letters[index] = set()
                self.yellow_letters[index].add(letter) # Letter is present, but not at this index
                current_positive_counts[letter] = current_positive_counts.get(letter, 0) + 1

            elif status == 'absent':
                # A letter is globally gray ONLY if it is NOT green or yellow anywhere in this guess
                is_globally_absent = True
                for l_check, s_check, _ in structured_feedback:
                    if l_check == letter and (s_check == 'correct' or s_check == 'present'):
                        is_globally_absent = False
                        break
                if is_globally_absent:
                    self.gray_letters.add(letter)

        # Update global minimum count based on green/yellow in the guess
        for letter, count in current_positive_counts.items():
             self.min_letter_counts[letter] = max(self.min_letter_counts.get(letter, 0), count)

        # If a gray letter was previously green/yellow, the MAX count is now known
        # Secret: VAZAR, Guess: PASSA -> Gray 'S' means exactly one 'S'
        for letter, status, index in structured_feedback:
            if status == 'absent' and letter in self.min_letter_counts:
                 # If letter appeared N times, K were green/yellow, and at least one gray,
                 # then the secret word has EXACTLY K occurrences.
                 # The maximum count is implicitly updated during filtering.
                 pass 

    # Checks if a word is consistent with all accumulated constraints.
    def _is_consistent(self, word):
        word_counts = {}
        for letter in word:
            word_counts[letter] = word_counts.get(letter, 0) + 1

        # Green constraints 
        for index, letter in self.green_letters.items():
            if index >= len(word) or word[index] != letter:
                return False

        # Yellow constraints 
        for index, letters_in_pos in self.yellow_letters.items():
            if index >= len(word): continue # Safety check
            # If a letter is yellow for a position, the candidate word cannot have it there
            if word[index] in letters_in_pos:
                return False
            # Also ensure that yellow letters must be present somewhere

        # 3. Gray constraints
        for letter in self.gray_letters:
            # If the letter is globally gray, it cannot be in the word,
            if letter in word and letter not in self.min_letter_counts:
                 return False

        # Minimum Count constraints
        for letter, min_count in self.min_letter_counts.items():
            # The letter must appear at least min_count times
            if word_counts.get(letter, 0) < min_count:
                return False

        # Maximum Count constraints 
        # If a letter 'L' appeared N times in guess, K were green/yellow, and P were gray (P>0),
        # then the secret word has EXACTLY K letters 'L'.
        for guess, structured_feedback in zip(self.guesses_history, self.feedback_history):
             guess_counts = {}
             positive_counts = {}
             has_gray = {}
             for i in range(self.word_length):
                 letter = guess[i]
                 status = structured_feedback[i][1]
                 guess_counts[letter] = guess_counts.get(letter, 0) + 1
                 if status == 'correct' or status == 'present':
                      positive_counts[letter] = positive_counts.get(letter, 0) + 1
                 if status == 'absent':
                      has_gray[letter] = True

             for letter in guess_counts:
                  # If the letter appeared in the guess, had gray occurrences, and is in the candidate word:
                  if has_gray.get(letter, False) and letter in word:
                       exact_count = positive_counts.get(letter, 0)
                       # The candidate word must have exactly this number of occurrences
                       if word_counts.get(letter, 0) != exact_count:
                            return False

        return True

    # Adds the result of a guess and filters the possible words
    def add_feedback(self, guess, structured_feedback):
    
        self.guesses_history.append(guess)
        self.feedback_history.append(structured_feedback)
        self._update_constraints(guess, structured_feedback)
        # Filter the list of possible words
        self.possible_words = {word for word in self.possible_words if self._is_consistent(word)}

    def get_next_guess(self, attempt_number):
        if attempt_number == 0:
            return "acelo"
        if attempt_number == 1:
            return "sumir"
        if not self.possible_words:
            print("Error: No possible words remaining! Check secret word.")
            # Fallback: choose a random word from the original list
            return random.choice(list(self.all_valid_words))
        if len(self.possible_words) == 1:
            return list(self.possible_words)[0]

        # Use OR-Tools to find ONE consistent word
        model = cp_model.CpModel()

        # Variables: one for each letter of the word
        letters = [model.NewIntVar(0, 25, f'l{i}') for i in range(self.word_length)] # 0='a', 1='b', ...

        # Main Constraint: The resulting word must be in the list of possible words
        allowed_tuples = []
        for word in self.possible_words:
            if len(word) == self.word_length: # Extra check
                allowed_tuples.append(tuple(ord(c) - ord('a') for c in word))

        if not allowed_tuples:
             print("Error: allowed_tuples set is empty for OR-Tools.")
             return random.choice(list(self.possible_words))

        # Add constraint that the letter combination MUST form one of the allowed words
        model.AddAllowedAssignments(letters, allowed_tuples)

        # Solve the model to find ONE solution
        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # Build the word from the found solution
            solution_indices = [solver.Value(l) for l in letters]
            guess = "".join(chr(idx + ord('a')) for idx in solution_indices)
            print(f"Debug: OR-Tools suggested: {guess}")
            return guess
        else:
            print(f"Warning: OR-Tools did not find a consistent solution (status={status}). Using random choice.")
            return random.choice(list(self.possible_words))

def play_game():
    print("\nWelcome to Termo in Python with CSP Solver!")
    valid_words = load_words(WORD_LIST_FILE)
    secret_word = choose_secret_word(valid_words)
    if not secret_word:
        print("Error: Could not choose a secret word.")
        return


    print(f"(Debug: The secret word is '{secret_word.upper()}')")
    
    print(f"The solver has {MAX_ATTEMPTS} attempts.")
    if not USE_COLORS:
         print(f"Feedback: {SYMBOL_CORRECT_POS}=Correct Position, {SYMBOL_WRONG_POS}=Letter Exists, {SYMBOL_ABSENT}=Letter Absent")

    # Instantiate the solver
    solver = TermoSolverCSP(valid_words, WORD_LENGTH)

    attempts_made = 0
    feedback_history_display = [] # To show the visual history

    while attempts_made < MAX_ATTEMPTS:
        print("-" * 30)
        print(f"Attempt {attempts_made + 1} of {MAX_ATTEMPTS}")
        current_guess = solver.get_next_guess(attempts_made)
        print(f"Solver guessed: {current_guess.upper()}")

        if current_guess not in valid_words:
             print(f"Warning: Solver generated an invalid word '{current_guess}'. Check logic.")
             # Try to recover by picking another random possible word
             if solver.possible_words:
                  current_guess = random.choice(list(solver.possible_words))
                  print(f"Recovery: Trying {current_guess.upper()}")
             else:
                   print("Critical Error: No more possible words for recovery.")
                   break

        # Check the guess and get feedback (visual and structured)
        visual_feedback, is_correct, structured_feedback = check_guess(current_guess, secret_word)
        # Add feedback to the solver
        solver.add_feedback(current_guess, structured_feedback)
        # Add visual feedback to the history for display
        feedback_history_display.append(visual_feedback)
        # Show the updated history, including the last attempt
        print("\nHistory:")
        for feedback_line in feedback_history_display:
            print(feedback_line)
        print(f"Possible words remaining: {len(solver.possible_words)}")
        print("-" * 20)


        if is_correct:
            print("\n" + "=" * 30)
            if USE_COLORS:
                print(f"{COLOR_GREEN}SOLVER GUESSED THE WORD!{COLOR_RESET}")
            else:
                print("SOLVER GUESSED THE WORD!")
            print(f"The word was: {secret_word.upper()}")
            print("=" * 30)
            return

        attempts_made += 1

    # If the loop finishes, the solver lost
    print("\n" + "=" * 30)
    if USE_COLORS:
        print(f"{COLOR_GRAY}Solver used all attempts!{COLOR_RESET}")
    else:
        print("Solver used all attempts!")
    print(f"The secret word was: {secret_word.upper()}")
    print(f"Words remaining as possibilities: {len(solver.possible_words)}")
    if len(solver.possible_words) < 10:
         print(f"Remaining possibilities: {sorted(list(solver.possible_words))}")
    print("=" * 30)


if __name__ == "__main__":
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        print("Error: The 'ortools' library is not installed. Install using: pip install ortools")
        sys.exit(1)

    play_game()
