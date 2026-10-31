"""Manage mandatory music credits without silently truncating API metadata."""
import re


def apply_credit(description, credit):
    description=re.sub(r'\n*\[Music attribution\].*?\[/Music attribution\]', '', description, flags=re.S)
    if credit:
        description+='\n\n[Music attribution]\n'+credit+'\n[/Music attribution]'
    if len(description)>5000:
        raise ValueError('Description plus mandatory music attribution exceeds 5000 characters; shorten editorial text')
    return description
