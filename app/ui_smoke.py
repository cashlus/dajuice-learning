# -*- coding: utf-8 -*-
import os
from streamlit.testing.v1 import AppTest

APP = r"C:\Users\cashrus\Documents\Codex\.kb\app\app.py"

at = AppTest.from_file(APP, default_timeout=60)
at.run()
print("exceptions:", [str(e.value) for e in at.exception])
print("selectbox count:", len(at.selectbox))
if at.selectbox:
    print("options:", at.selectbox[0].options)
    print("selected:", at.selectbox[0].value)
print("text_area count:", len(at.text_area))
print("buttons:", [(b.label, b.key) for b in at.button])
print("expanders:", [(e.label, e.expanded) for e in at.expander])