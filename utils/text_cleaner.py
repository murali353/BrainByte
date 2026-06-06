import re

def clean_pdf_text(text):

    # REMOVE EXTRA SPACES
    text = re.sub(r'\s+', ' ', text)

    # REMOVE PAGE NUMBERS
    text = re.sub(r'Page \d+', '', text)

    # REMOVE REPEATED HEADERS
    text = re.sub(r'VTU.*?University', '', text)

    # REMOVE SPECIAL BROKEN CHARACTERS
    text = re.sub(r'[^a-zA-Z0-9.,:;()%/\-\s]', '', text)

    # REMOVE MULTIPLE SPACES AGAIN
    text = re.sub(r'\s+', ' ', text)

    return text.strip()
