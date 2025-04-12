import unicodedata

def remove_accents(text):
  """Removes accents from a string using Unicode normalization."""
  # Normalize the string to NFD
  normalized_text = unicodedata.normalize('NFD', text)
  # Filter the string, keeping only characters that are not combining diacritical marks (category 'Mn')
  without_accents = ''.join(c for c in normalized_text if unicodedata.category(c) != 'Mn')
  return without_accents

# File names
input_filename = 'palavras.txt'
output_filename = 'palavras_5letras.txt'

# Set to store the 5-letter words, without accents and without repetition
unique_5letter_words = set()

try:
  # Open the input file for reading with UTF-8 encoding
  with open(input_filename, 'r', encoding='utf-8') as f_in:
    print(f"Reading file '{input_filename}'...")
    for line in f_in:
      original_word = line.strip()

      # Check if the original word has exactly 5 letters
      if len(original_word) == 5:
        # Convert to lowercase to prevent duplicates due to case
        lower_word = original_word.lower()
        # Remove accents from the word
        word_without_accent = remove_accents(lower_word)

        # Add the processed word to the set
        unique_5letter_words.add(word_without_accent)

  print(f"Processing complete. {len(unique_5letter_words)} unique 5-letter words found.")

  # Convert the set to a list and sort it alphabetically
  sorted_words = sorted(list(unique_5letter_words))

  # Open the output file for writing
  with open(output_filename, 'w', encoding='utf-8') as f_out:
    print(f"Writing words to file '{output_filename}'...")
    # Write each sorted word to the output file, one per line
    for word in sorted_words:
      f_out.write(word + '\n') # Add a newline character after each word

  print(f"File '{output_filename}' created successfully!")

# Error handling in case the input file is not found
except FileNotFoundError:
  print(f"Error: Input file '{input_filename}' not found.")
  print("Please ensure the file exists in the same directory as the script or provide the correct path.")

# Handling other unexpected errors
except Exception as e:
  print(f"An unexpected error occurred during processing: {e}")
