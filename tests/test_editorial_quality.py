from scripts.editorial_quality import estimated_duration_seconds, script_diagnostics

CLASSIC_OPENING = ("Bienvenidos a NewSphere. Hoy vamos a hablar de la huelga educativa en Madrid. "
                   "Antes de seguir, suscríbete y activa la campana. ")
FACT_OPENING = ("La Comunidad de Madrid endurece hoy los servicios mínimos de la huelga educativa. "
                "Un docente por cada cincuenta alumnos en Infantil. ")
BODY = "Los sindicatos preparan medidas cautelares contra la nueva orden de servicios mínimos. " * 30


def _project(script, editorial_format=None, target=240):
    brief = {"target_duration_seconds": target, "duration_tolerance_seconds": 15}
    if editorial_format:
        brief["editorial_format"] = editorial_format
    return {"script": script, "narration": [{"text": script}], "editorial_brief": brief}


def test_classic_template_welcome_is_not_flagged():
    result = script_diagnostics(_project(CLASSIC_OPENING + BODY))
    assert result["generic_opening"] is False
    assert result["early_cta_in_editorial_format"] is False


def test_editorial_format_requires_a_fact_first_and_late_cta():
    welcome = script_diagnostics(_project(CLASSIC_OPENING + BODY, "DAILY_BRIEF", 360))
    assert welcome["generic_opening"] is True
    assert welcome["early_cta_in_editorial_format"] is True
    fact = script_diagnostics(_project(FACT_OPENING + BODY + "Suscríbete.", "DAILY_BRIEF", 360))
    assert fact["generic_opening"] is False
    assert fact["early_cta_in_editorial_format"] is False


def test_length_problems_are_reported_before_voice_synthesis():
    script = FACT_OPENING + BODY
    result = script_diagnostics(_project(script, target=60))
    assert result["measured_duration_seconds"] is None
    assert result["estimated_duration_seconds"] == estimated_duration_seconds(script)
    assert result["outside_target_duration"] is True
    fitting = script_diagnostics(_project(script, target=round(result["estimated_duration_seconds"])))
    assert fitting["outside_target_duration"] is False


def test_measured_duration_overrides_the_estimate():
    result = script_diagnostics(_project(FACT_OPENING, target=233), duration=233.0)
    assert result["outside_target_duration"] is False
