import re

def chunk_text(text, max_words=1200):

    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []

    current_chunk = []

    current_words = 0

    for sentence in sentences:

        word_count = len(sentence.split())

        if current_words + word_count > max_words:

            chunks.append(
                " ".join(current_chunk)
            )

            current_chunk = [sentence]

            current_words = word_count

        else:

            current_chunk.append(sentence)

            current_words += word_count

    if current_chunk:

        chunks.append(
            " ".join(current_chunk)
        )

    return chunks
