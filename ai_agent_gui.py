import sys
from PySide6.QtCore import QAbstractListModel, QMargins, QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QFontMetrics, QMovie, QIcon, QFont
from PySide6.QtWidgets import (
    QApplication, QLineEdit, QListView, QMainWindow, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QStyledItemDelegate, 
    QListWidget, QStackedWidget, QLabel, QFormLayout, QDialogButtonBox, 
    QDialog, QMessageBox
)
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
from langchain.agents.agent_types import AgentType
import pandas as pd
from pinecone import Pinecone
from dotenv import load_dotenv
import os
import requests
import uuid


USER_ME = 0
USER_THEM = 1

BUBBLE_COLORS = {USER_ME: "#90caf9", USER_THEM: "#a5d6a7"}

BUBBLE_PADDING = QMargins(15, 5, 15, 5)
TEXT_PADDING = QMargins(25, 15, 25, 15)

NAMESPACE_ID = None

# Draws each message.
class MessageDelegate(QStyledItemDelegate):

    def paint(self, painter, option, index):
        # Retrieve the user, message tuple from our model.data method.
        user, text = index.model().data(index, Qt.DisplayRole)

        # option.rect contains our item dimensions. We need to pad it a bit
        # to give us space from the edge to draw our shape.
        bubblerect = option.rect.marginsRemoved(BUBBLE_PADDING)
        textrect = option.rect.marginsRemoved(TEXT_PADDING)

        # draw the bubble, changing color + arrow position depending on who
        # sent the message. the bubble is a rounded rect, with a triangle in
        # the edge.
        painter.setPen(Qt.NoPen)
        color = QColor(BUBBLE_COLORS[user])
        painter.setBrush(color)
        painter.drawRoundedRect(bubblerect, 10, 10)

        # draw the triangle bubble-pointer, starting from
        if user == USER_ME:
            p1 = bubblerect.topRight()
        else:
            p1 = bubblerect.topLeft()
        painter.drawPolygon([p1 + QPoint(-20, 0), p1 + QPoint(20, 0), p1 + QPoint(0, 20)])

        # draw the text
        if isinstance(text, str):
            painter.setPen(Qt.black)
            painter.drawText(textrect, Qt.TextWordWrap, text)

    def sizeHint(self, option, index):
        _, text = index.model().data(index, Qt.DisplayRole)
        # Calculate the dimensions the text will require.
        metrics = QFontMetrics(option.font)
        rect = option.rect.marginsRemoved(TEXT_PADDING)
        if isinstance(text, str):
            rect = metrics.boundingRect(rect, Qt.TextWordWrap, text)
        rect = rect.marginsAdded(TEXT_PADDING)  # Re-add padding for item size.
        return rect.size()


class MessageModel(QAbstractListModel):
    def __init__(self, *args, **kwargs):
        super(MessageModel, self).__init__(*args, **kwargs)
        self.messages = []

    def data(self, index, role):
        if role == Qt.DisplayRole:
            # Here we pass the delegate the user, message tuple.
            return self.messages[index.row()]

    def rowCount(self, index):
        return len(self.messages)

    def add_message(self, who, text):
        if text:  # Don't add empty strings.
            # Access the list via the model.
            self.messages.append((who, text))
            # Trigger refresh.
            self.layoutChanged.emit()


def query_prediction(payload):
    PREDICT_URL = os.getenv("PREDICT_URL")
    response = requests.post(PREDICT_URL, json=payload)
    return response.json()


class PDFChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.messages = QListView()
        self.messages.setItemDelegate(MessageDelegate())
        self.model = MessageModel()
        self.messages.setModel(self.model)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(" Enter Your Query Here... ")

        self.upload_button = QPushButton("Upload PDF", self)
        self.upload_button.clicked.connect(self.upload_pdf)

        self.send_button = QPushButton("Send", self)
        self.send_button.clicked.connect(self.send_query)

        self.layout.addWidget(self.messages)
        self.layout.addWidget(self.input_field)
        self.layout.addWidget(self.upload_button)
        self.layout.addWidget(self.send_button)

        self.namespace_id = None

    def upload_pdf(self):
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if file_path:
            self.upload_button.setEnabled(False)
            self.upload_button.setText("Loading")

            # Add a small delay before starting the upsert process
            QTimer.singleShot(100, lambda: self.start_upsert(file_path))

    def start_upsert(self, file_path):
        try:
            # Generate a unique namespace ID
            self.namespace_id = str(uuid.uuid4())

            output = self.upsert(file_path, self.namespace_id)

            if "successfully upserted" in output:
                self.model.add_message(USER_THEM, "PDF file successfully upserted!")
                self.upload_button.setText("PDF Upserted")
            else:
                self.model.add_message(USER_THEM, str(output))
                self.upload_button.setText("Upload PDF")
                self.upload_button.setEnabled(True)

            self.messages.scrollToBottom()
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            self.model.add_message(USER_THEM, error_message)
            self.upload_button.setText("Upload PDF")
            self.upload_button.setEnabled(True)
        finally:
            self.upload_button.setIcon(QIcon())

    def upsert(self, file_path, namespace):
        filename = os.path.basename(file_path)
        form_data = {"files": (filename, open(file_path, 'rb'), 'application/pdf')}
        body_data = {"pineconeNamespace": namespace}

        PDF_UPSERT_URL = os.getenv("PDF_UPSERT_URL")
        response = requests.post(PDF_UPSERT_URL, files=form_data, data=body_data)

        if response.status_code == 201:
            return "Document successfully upserted!"
        else:
            try:
                error_message = response.json().get("message", "Unknown error")
                return f"Error: {error_message}"
            except requests.exceptions.JSONDecodeError:
                return "Error: Invalid JSON response from the API"

    def send_query(self):
        if self.upload_button.text() == "PDF Upserted":
            query = self.input_field.text()
            if query:
                self.model.add_message(USER_ME, query)
                self.input_field.clear()
                self.messages.scrollToBottom()

                self.send_button.setEnabled(False)
                self.send_button.setText("Loading")

                # Add a small delay before sending the query
                QTimer.singleShot(100, lambda: self.start_query(query))
        else:
            self.model.add_message(USER_THEM, "Please upload a PDF file first.")

    def start_query(self, query):
        try:
            payload = {
                "question": query,
                "overrideConfig":{
                "pineconeNamespace": self.namespace_id
                }
            }

            output = query_prediction(payload)

            if "text" in output:
                response_text = output["text"]
                self.model.add_message(USER_THEM, response_text)
            else:
                self.model.add_message(USER_THEM, "Sorry, I couldn't generate a response.")

            self.messages.scrollToBottom()
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            self.model.add_message(USER_THEM, error_message)
        finally:
            self.send_button.setText("Send")
            self.send_button.setEnabled(True)


class DOCXChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.messages = QListView()
        self.messages.setItemDelegate(MessageDelegate())
        self.model = MessageModel()
        self.messages.setModel(self.model)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(" Enter Your Query Here... ")

        self.upload_button = QPushButton("Upload DOCX", self)
        self.upload_button.clicked.connect(self.upload_docx)

        self.send_button = QPushButton("Send", self)
        self.send_button.clicked.connect(self.send_query)

        self.layout.addWidget(self.messages)
        self.layout.addWidget(self.input_field)
        self.layout.addWidget(self.upload_button)
        self.layout.addWidget(self.send_button)

        self.namespace_id = None

    def upload_docx(self):
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(self, "Open DOCX", "", "DOCX Files (*.docx)")
        if file_path:
            self.upload_button.setEnabled(False)
            self.upload_button.setText("Loading")

            # Add a small delay before starting the upsert process
            QTimer.singleShot(100, lambda: self.start_upsert(file_path))

    def start_upsert(self, file_path):
        try:
            # Generate a unique namespace ID
            self.namespace_id = str(uuid.uuid4())

            output = self.upsert(file_path, self.namespace_id)

            if "successfully upserted" in output:
                self.model.add_message(USER_THEM, "DOCX file successfully upserted!")
                self.upload_button.setText("DOCX Upserted")
            else:
                self.model.add_message(USER_THEM, str(output))
                self.upload_button.setText("Upload DOCX")
                self.upload_button.setEnabled(True)

            self.messages.scrollToBottom()
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            self.model.add_message(USER_THEM, error_message)
            self.upload_button.setText("Upload DOCX")
            self.upload_button.setEnabled(True)
        finally:
            self.upload_button.setIcon(QIcon())

    def upsert(self, file_path, namespace):
        filename = os.path.basename(file_path)
        form_data = {"files": (filename, open(file_path, 'rb'), 'application/docx')}
        body_data = {"pineconeNamespace": namespace}

        DOCX_UPSERT_URL = os.getenv("DOCX_UPSERT_URL")
        response = requests.post(DOCX_UPSERT_URL, files=form_data, data=body_data)

        if response.status_code == 201:
            return "Document successfully upserted!"
        else:
            try:
                error_message = response.json().get("message", "Unknown error")
                return f"Error: {error_message}"
            except requests.exceptions.JSONDecodeError:
                return "Error: Invalid JSON response from the API"

    def send_query(self):
        if self.upload_button.text() == "DOCX Upserted":
            query = self.input_field.text()
            if query:
                self.model.add_message(USER_ME, query)
                self.input_field.clear()
                self.messages.scrollToBottom()

                self.send_button.setEnabled(False)
                self.send_button.setText("Loading")

                # Add a small delay before sending the query
                QTimer.singleShot(100, lambda: self.start_query(query))
        else:
            self.model.add_message(USER_THEM, "Please upload a DOCX file first.")

    def start_query(self, query):
        try:
            payload = {
                "question": query,
                "overrideConfig":{
                "pineconeNamespace": self.namespace_id
                }
            }

            output = query_prediction(payload)

            if "text" in output:
                response_text = output["text"]
                self.model.add_message(USER_THEM, response_text)
            else:
                self.model.add_message(USER_THEM, "Sorry, I couldn't generate a response.")

            self.messages.scrollToBottom()
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            self.model.add_message(USER_THEM, error_message)
        finally:
            self.send_button.setText("Send")
            self.send_button.setEnabled(True)


class WEBChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.messages = QListView()
        self.messages.setItemDelegate(MessageDelegate())
        self.model = MessageModel()
        self.messages.setModel(self.model)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(" Enter Your Query Here... ")

        self.upload_button = QPushButton("Upload Webpage", self)
        self.upload_button.clicked.connect(self.upload_web)

        self.send_button = QPushButton("Send", self)
        self.send_button.clicked.connect(self.send_query)

        self.layout.addWidget(self.messages)
        self.layout.addWidget(self.input_field)
        self.layout.addWidget(self.upload_button)
        self.layout.addWidget(self.send_button)

        self.namespace_id = None

    def upload_web(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Enter Webpage URL")
        dialog.setFixedSize(400, 100)
        layout = QVBoxLayout(dialog)

        url_input = QLineEdit(dialog)
        url_input.setPlaceholderText("Enter the webpage URL")
        layout.addWidget(url_input)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() == QDialog.Accepted:
            url = url_input.text()
            if url:
                self.upload_button.setEnabled(False)
                self.upload_button.setText("Loading")

                # Add a small delay before starting the upsert process
                QTimer.singleShot(100, lambda: self.start_upsert(url))

    def start_upsert(self, url):
        try:
            # Generate a unique namespace ID
            self.namespace_id = str(uuid.uuid4())

            output = self.upsert(url, self.namespace_id)

            if "successfully upserted" in output:
                self.model.add_message(USER_THEM, "Webpage successfully upserted!")
                self.upload_button.setText("Webpage Upserted")
            else:
                self.model.add_message(USER_THEM, str(output))
                self.upload_button.setText("Upload Webpage")
                self.upload_button.setEnabled(True)

            self.messages.scrollToBottom()
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            self.model.add_message(USER_THEM, error_message)
            self.upload_button.setText("Upload Webpage")
            self.upload_button.setEnabled(True)
        finally:
            self.upload_button.setIcon(QIcon())

    def upsert(self, url, namespace):
        payload = {
            "overrideConfig": {
                "pineconeNamespace": namespace,
                "url": url
            }
        }

        WEB_UPSERT_URL = os.getenv("WEB_UPSERT_URL")
        response = requests.post(WEB_UPSERT_URL, json=payload)

        if response.status_code == 201:
            return "Webpage successfully upserted!"
        else:
            try:
                error_message = response.json().get("message", "Unknown error")
                return f"Error: {error_message}"
            except requests.exceptions.JSONDecodeError:
                return "Error: Invalid JSON response from the API"

    def send_query(self):
        if self.upload_button.text() == "Webpage Upserted":
            query = self.input_field.text()
            if query:
                self.model.add_message(USER_ME, query)
                self.input_field.clear()
                self.messages.scrollToBottom()

                self.send_button.setEnabled(False)
                self.send_button.setText("Loading")

                # Add a small delay before sending the query
                QTimer.singleShot(100, lambda: self.start_query(query))
        else:
            self.model.add_message(USER_THEM, "Please upload a Webpage first.")

    def start_query(self, query):
        try:
            payload = {
                "question": query,
                "overrideConfig": {
                    "pineconeNamespace": self.namespace_id
                }
            }

            output = query_prediction(payload)

            if "text" in output:
                response_text = output["text"]
                self.model.add_message(USER_THEM, response_text)
            else:
                self.model.add_message(USER_THEM, "Sorry, I couldn't generate a response.")

            self.messages.scrollToBottom()
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            self.model.add_message(USER_THEM, error_message)
        finally:
            self.send_button.setText("Send")
            self.send_button.setEnabled(True)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("AI AGENT GUI")
        self.setWindowIcon(QIcon("icon.png"))

        # Fixed size for the main window
        self.setFixedSize(800, 530)

        central_widget = QWidget(self)
        main_layout = QHBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        side_menu_layout = QVBoxLayout()
        side_menu_layout.setAlignment(Qt.AlignTop)
        side_menu_layout.setContentsMargins(0,12,0,0)

        # Create side menu
        self.side_menu = QListWidget()
        self.side_menu.setFixedSize(90, 365)
        self.side_menu.addItem("PANDAS UI")
        self.side_menu.addItem("PDF CHAT")
        self.side_menu.addItem("DOCX CHAT")
        self.side_menu.addItem("WEB CHAT")
        self.side_menu.itemClicked.connect(self.switch_menu)
        side_menu_layout.addWidget(self.side_menu)

        main_layout.addLayout(side_menu_layout)

        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create agent widget
        self.agent_widget = QWidget()
        agent_layout = QVBoxLayout(self.agent_widget)
        self.stacked_widget.addWidget(self.agent_widget)

        # Create PDF chat widget
        self.pdf_chat_widget = PDFChatWidget()
        self.stacked_widget.addWidget(self.pdf_chat_widget)

        # Create DOCX chat widget
        self.docx_chat_widget = DOCXChatWidget()
        self.stacked_widget.addWidget(self.docx_chat_widget)

        # Create WEB chat widget
        self.web_chat_widget = WEBChatWidget()
        self.stacked_widget.addWidget(self.web_chat_widget)

        # Create toolbar
        toolbar = self.addToolBar("Configuration")
        openai_action = toolbar.addAction("OpenAI", lambda: self.show_config_dialog("OpenAI"))
        flowise_action = toolbar.addAction("Flowise", lambda: self.show_config_dialog("Flowise"))
        pinecone_action = toolbar.addAction("Pinecone", lambda: self.show_config_dialog("Pinecone"))

        self.messages = QListView()
        self.messages.setItemDelegate(MessageDelegate())
        self.model = MessageModel()
        self.messages.setModel(self.model)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(" Upload CSV and Enter Your Query Here... ")
        upload_button = QPushButton("Upload CSV", self)
        upload_button.clicked.connect(self.upload_csv)
        self.send_button = QPushButton("Send", self)
        self.send_button.clicked.connect(self.send_query)

        agent_layout.addWidget(self.messages)
        agent_layout.addWidget(self.input_field)
        agent_layout.addWidget(upload_button)
        agent_layout.addWidget(self.send_button)

        # Load credentials
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")

        if not api_key:
            QMessageBox.information(self, "Update .env file", "OpenAI API Key Not Found! Please Update .env File")
            sys.exit()  

        # Initialize language model for agent
        self.llm = ChatOpenAI(model_name="gpt-3.5-turbo-0125", temperature=0, openai_api_key=api_key)

        self.df = None


    def switch_menu(self, item):
        if item.text() == "PANDAS UI":
            self.stacked_widget.setCurrentWidget(self.agent_widget)
        elif item.text() == "PDF CHAT":
            self.stacked_widget.setCurrentWidget(self.pdf_chat_widget)
        elif item.text() == "DOCX CHAT":
            self.stacked_widget.setCurrentWidget(self.docx_chat_widget)
        elif item.text() == "WEB CHAT":
            self.stacked_widget.setCurrentWidget(self.web_chat_widget)

    def upload_csv(self):
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")
        if file_path:
            self.df = pd.read_csv(file_path)
            self.model.add_message(USER_THEM, "CSV file uploaded successfully.")
            self.messages.scrollToBottom()


    def send_query(self):
        prefix = """
        When responding, please follow this ONLY guideline:
        *Wrap your entire answer in <answer>...</answer> tags*.
        DO NOT WRAP ANYTHING ELSE WITH TAGS
        """
        query = self.input_field.text()
        final_query = f"{prefix} {query}"

        if query.lower() == 'exit':
            self.close()
        else:
            self.model.add_message(USER_ME, query)
            self.input_field.clear()
            self.messages.scrollToBottom()

            self.send_button.setEnabled(False)
            self.send_button.setText("Loading")

            QTimer.singleShot(100, lambda: self.run_agent_query(final_query))

    def run_agent_query(self, query):
        try:
            if self.df is not None:
                agent = create_pandas_dataframe_agent(self.llm, self.df, verbose=True, agent_type=AgentType.OPENAI_FUNCTIONS)
                result = agent.invoke({"input": query})
                response = self.extract_response(result)
                self.model.add_message(USER_THEM, response)
                self.messages.scrollToBottom()
            else:
                self.model.add_message(USER_THEM, "Please upload a CSV file first.")
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            self.model.add_message(USER_THEM, error_message)

        self.send_button.setIcon(QIcon())  
        self.send_button.setText("Send")
        self.send_button.setEnabled(True)

    def extract_response(self, result):
        start_tag = "<answer>"
        end_tag = "</answer>"

        if isinstance(result, dict) and "output" in result:
            output = result["output"]
            start_index = output.find(start_tag)
            end_index = output.find(end_tag)

            if start_index != -1 and end_index != -1:
                start_index += len(start_tag)
                response = output[start_index:end_index].strip()
            else:
                response = "Sorry, I couldn't generate a proper response."
        else:
            response = "Sorry, I couldn't generate a proper response."

        return response

    def show_config_dialog(self, config_type):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{config_type} Configuration")
        layout = QVBoxLayout(dialog)

        if config_type == "OpenAI":
            dialog.setFixedSize(400, 115)
            api_key_input = QLineEdit(dialog)
            api_key_input.setEchoMode(QLineEdit.Password)

            font = QFont()
            # font.setBold(True)
            font.setUnderline(True)
            api_key_label = QLabel("OpenAI API Key:")
            api_key_label.setFont(font)

            layout.addWidget(api_key_label)
            layout.addWidget(api_key_input)

            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                api_key_input.setText(api_key)
        elif config_type == "Flowise":
            dialog.setFixedSize(650, 300)  
            pdf_upsert_url_input = QLineEdit(dialog)
            docx_upsert_url_input = QLineEdit(dialog)
            web_upsert_url_input = QLineEdit(dialog)
            predict_url_input = QLineEdit(dialog)

            font = QFont()
            font.setUnderline(True)
            # font.setBold(True)

            pdf_upsert_label = QLabel("PDF Upsert URL:")
            pdf_upsert_label.setFont(font)
            layout.addWidget(pdf_upsert_label)
            layout.addWidget(pdf_upsert_url_input)

            docx_upsert_label = QLabel("DOCX Upsert URL:")
            docx_upsert_label.setFont(font)
            layout.addWidget(docx_upsert_label)
            layout.addWidget(docx_upsert_url_input)

            web_upsert_label = QLabel("WEB Upsert URL:")
            web_upsert_label.setFont(font)
            layout.addWidget(web_upsert_label)
            layout.addWidget(web_upsert_url_input)

            predict_url_label = QLabel("Load URL:")
            predict_url_label.setFont(font)
            layout.addWidget(predict_url_label)
            layout.addWidget(predict_url_input)

            # Load saved Flowise URLs
            pdf_upsert_url = os.getenv("PDF_UPSERT_URL")
            if pdf_upsert_url:
                pdf_upsert_url_input.setText(pdf_upsert_url)

            docx_upsert_url = os.getenv("DOCX_UPSERT_URL")
            if docx_upsert_url:
                docx_upsert_url_input.setText(docx_upsert_url)

            web_upsert_url = os.getenv("WEB_UPSERT_URL")
            if web_upsert_url:
                web_upsert_url_input.setText(web_upsert_url)

            predict_url = os.getenv("PREDICT_URL")
            if predict_url:
                predict_url_input.setText(predict_url)
        else:  # Pinecone 
            dialog.setFixedSize(400, 200) 
            api_key_input = QLineEdit(dialog)
            api_key_input.setEchoMode(QLineEdit.Password)
            index_name_input = QLineEdit(dialog)

            font = QFont()
            font.setUnderline(True)

            api_key_label = QLabel("Pinecone API Key:")
            api_key_label.setFont(font)
            layout.addWidget(api_key_label)
            layout.addWidget(api_key_input)

            index_name_label = QLabel("Pinecone Index Name:")
            index_name_label.setFont(font)
            layout.addWidget(index_name_label)
            layout.addWidget(index_name_input)

            api_key = os.getenv("PINECONE_API_KEY")
            if api_key:
                api_key_input.setText(api_key)

            index_name = os.getenv("PINECONE_INDEX_NAME")
            if index_name:
                index_name_input.setText(index_name)

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, dialog)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() == QDialog.Accepted:
            os.environ = {}
            with open(".env", "r") as f:
                for line in f:
                    if line.strip():
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value

            if config_type == "OpenAI":
                api_key = api_key_input.text()
                os.environ["OPENAI_API_KEY"] = api_key
            elif config_type == "Flowise":
                pdf_upsert_url = pdf_upsert_url_input.text()
                docx_upsert_url = docx_upsert_url_input.text()
                web_upsert_url = web_upsert_url_input.text()
                predict_url = predict_url_input.text()

                os.environ["PDF_UPSERT_URL"] = pdf_upsert_url
                os.environ["DOCX_UPSERT_URL"] = docx_upsert_url
                os.environ["WEB_UPSERT_URL"] = web_upsert_url
                os.environ["PREDICT_URL"] = predict_url
            else:  # Pinecone section
                api_key = api_key_input.text()
                index_name = index_name_input.text()

                os.environ["PINECONE_API_KEY"] = api_key
                os.environ["PINECONE_INDEX_NAME"] = index_name

            # Write the updated environment variables back to the .env file
            with open(".env", "w") as f:
                for key, value in os.environ.items():
                    f.write(f"{key}={value}\n")

            QMessageBox.information(self, "Configuration Saved", "Configuration saved successfully!")

    def closeEvent(self, event):
        # Delete all records from Pinecone namespaces on close
        self.delete_pinecone_records()
        event.accept()

    def delete_pinecone_records(self):
        load_dotenv()
        api_key = os.getenv("PINECONE_API_KEY")
        index_name = os.getenv("PINECONE_INDEX_NAME")

        if api_key and index_name:
            try:
                pc = Pinecone(api_key=api_key)
                index = pc.Index(index_name)

                # Delete records from PDF namespace
                if self.pdf_chat_widget.namespace_id:
                    index.delete(delete_all=True, namespace=self.pdf_chat_widget.namespace_id)

                # Delete records from DOCX namespace
                if self.docx_chat_widget.namespace_id:
                    index.delete(delete_all=True, namespace=self.docx_chat_widget.namespace_id)

                # Delete records from WEB namespace
                if self.web_chat_widget.namespace_id:
                    index.delete(delete_all=True, namespace=self.web_chat_widget.namespace_id)

                print("Pinecone records deleted successfully.")
            except Exception as e:
                print(f"Error deleting Pinecone records: {str(e)}")
        else:
            print("Pinecone API key or index name not found in .env file.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
