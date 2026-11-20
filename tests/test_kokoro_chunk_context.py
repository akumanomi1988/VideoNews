from scripts.kokoro_worker import chunks


def test_introductions_keep_their_acoustic_context():
    text = "Pensemos en un engranaje: una rueda mueve la siguiente; ambas necesitan espacio."
    assert chunks(text) == [text]


def test_context_preserves_encoder_bound_and_all_words():
    text = "Una introducción: " + "explicación " * 80
    result = chunks(text)
    assert all(len(part) <= 260 for part in result)
    assert " ".join(result).split() == text.split()


def test_short_question_joins_the_following_sentence():
    text = ("La huelga lleva más de un mes en la educación pública madrileña. ¿Qué piden? "
            "Menos horas lectivas, una subida salarial y menos alumnos por aula.")
    result = chunks(text)
    assert result == [
        "La huelga lleva más de un mes en la educación pública madrileña.",
        "¿Qué piden? Menos horas lectivas, una subida salarial y menos alumnos por aula.",
    ]


def test_short_closing_line_joins_the_previous_sentence():
    text = ("Gracias por acompañarnos hoy en NewSphere y hasta la próxima semana. "
            "Comparte y comenta.")
    assert chunks(text) == [text]


def test_merging_never_drops_words_or_exceeds_limit():
    sentence = "Palabra " * 30
    text = "Uno dos. " + sentence.strip() + ". Tres. " + sentence.strip() + ". Fin."
    result = chunks(text)
    assert " ".join(result).split() == text.split()
    assert all(len(part) <= 260 for part in result)
    assert all(len(part.split()) >= 2 for part in result)
