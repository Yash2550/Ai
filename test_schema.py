import os
os.environ["RECRAFT_API_KEY"] = "fake"
os.environ["NANOBANANA_API_KEY"] = "fake"
import gradio_app
gradio_app.demo.get_api_info()
print("Success")
