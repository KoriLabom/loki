from loki.estados import Estado, MaquinaEstados


def test_wake_word_pasa_de_dormido_a_escuchando():
    m = MaquinaEstados()
    m.wake_word_detectada()
    assert m.estado == Estado.ESCUCHANDO


def test_fin_de_voz_pasa_de_escuchando_a_pensando():
    m = MaquinaEstados(estado_inicial=Estado.ESCUCHANDO)
    m.fin_de_voz()
    assert m.estado == Estado.PENSANDO


def test_sin_voz_tras_activacion_vuelve_a_dormido():
    m = MaquinaEstados(estado_inicial=Estado.ESCUCHANDO)
    m.sin_voz_tras_activacion()
    assert m.estado == Estado.DORMIDO


def test_primera_oracion_lista_pasa_de_pensando_a_hablando():
    m = MaquinaEstados(estado_inicial=Estado.PENSANDO)
    m.primera_oracion_lista()
    assert m.estado == Estado.HABLANDO


def test_fin_de_reproduccion_vuelve_a_dormido():
    m = MaquinaEstados(estado_inicial=Estado.HABLANDO)
    m.fin_de_reproduccion()
    assert m.estado == Estado.DORMIDO


def test_wake_word_durante_hablando_interrumpe_y_pasa_a_escuchando():
    m = MaquinaEstados(estado_inicial=Estado.HABLANDO)
    transiciones = []
    m.observar(lambda anterior, nuevo: transiciones.append((anterior, nuevo)))

    m.wake_word_detectada()

    assert m.estado == Estado.ESCUCHANDO
    assert transiciones == [(Estado.HABLANDO, Estado.ESCUCHANDO)]


def test_wake_word_mientras_ya_esta_escuchando_no_hace_nada():
    m = MaquinaEstados(estado_inicial=Estado.ESCUCHANDO)
    transiciones = []
    m.observar(lambda anterior, nuevo: transiciones.append((anterior, nuevo)))

    m.wake_word_detectada()

    assert m.estado == Estado.ESCUCHANDO
    assert transiciones == []


def test_observadores_reciben_estado_anterior_y_nuevo_en_orden():
    m = MaquinaEstados()
    transiciones = []
    m.observar(lambda anterior, nuevo: transiciones.append((anterior, nuevo)))

    m.wake_word_detectada()
    m.fin_de_voz()
    m.primera_oracion_lista()
    m.fin_de_reproduccion()

    assert transiciones == [
        (Estado.DORMIDO, Estado.ESCUCHANDO),
        (Estado.ESCUCHANDO, Estado.PENSANDO),
        (Estado.PENSANDO, Estado.HABLANDO),
        (Estado.HABLANDO, Estado.DORMIDO),
    ]


def test_agente_trabajando_es_un_estado_paralelo_independiente():
    m = MaquinaEstados()
    assert not m.hay_agentes_trabajando

    m.agente_empezo_a_trabajar("terminal-1")
    assert m.hay_agentes_trabajando
    assert m.estado == Estado.DORMIDO  # no afecta el estado principal

    m.agente_empezo_a_trabajar("terminal-2")
    m.agente_termino_de_trabajar("terminal-1")
    assert m.hay_agentes_trabajando  # todavía queda terminal-2

    m.agente_termino_de_trabajar("terminal-2")
    assert not m.hay_agentes_trabajando
