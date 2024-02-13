def ftitle(value):
    words = value.split('_')
    capitalized_words = [word.capitalize() for word in words]
    return ' '.join(capitalized_words)
