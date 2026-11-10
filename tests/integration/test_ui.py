from streamlit.testing.v1 import AppTest


def test_sample_and_complete_audit():
    app = AppTest.from_file("app/main.py", default_timeout=60).run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert app.metric[0].value != "0.00"
    next(b for b in app.button if b.label == "Run complete deterministic audit").click().run()
    assert not app.exception
    assert app.session_state["audit"]["report"]["mode"] == "deterministic"
    assert len(app.session_state["audit"]["results"]) == 4
