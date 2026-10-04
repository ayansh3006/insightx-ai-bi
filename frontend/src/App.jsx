import { useRef, useState } from "react";
import {
  Upload,
  FileSpreadsheet,
  Send,
  Database,
  Sparkles,
  CheckCircle2,
  X,
  Loader2,
  BarChart3,
} from "lucide-react";

import "./App.css";


const API_BASE_URL = "http://127.0.0.1:8000";


function App() {
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);

  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");

  const [dragActive, setDragActive] = useState(false);


  // --------------------------------------------------
  // FILE VALIDATION
  // --------------------------------------------------

  const validateFile = (selectedFile) => {
    if (!selectedFile) {
      return false;
    }

    const extension = selectedFile.name
      .split(".")
      .pop()
      .toLowerCase();

    if (!["csv", "xlsx"].includes(extension)) {
      setError("Please upload a CSV or XLSX file.");
      return false;
    }

    return true;
  };


  // --------------------------------------------------
  // FILE SELECTION
  // --------------------------------------------------

  const handleFileSelect = (selectedFile) => {
    setError("");

    if (!validateFile(selectedFile)) {
      return;
    }

    setFile(selectedFile);
    setDataset(null);
    setAnswer(null);
  };


  // --------------------------------------------------
  // INPUT CHANGE
  // --------------------------------------------------

  const handleFileInput = (event) => {
    const selectedFile = event.target.files?.[0];

    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  };


  // --------------------------------------------------
  // DRAG EVENTS
  // --------------------------------------------------

  const handleDragOver = (event) => {
    event.preventDefault();
    setDragActive(true);
  };


  const handleDragLeave = () => {
    setDragActive(false);
  };


  const handleDrop = (event) => {
    event.preventDefault();
    setDragActive(false);

    const droppedFile = event.dataTransfer.files?.[0];

    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  };


  // --------------------------------------------------
  // UPLOAD DATASET
  // --------------------------------------------------

  const uploadDataset = async () => {
    if (!file) {
      setError("Please select a dataset first.");
      return;
    }

    setUploading(true);
    setError("");
    setAnswer(null);

    try {
      const formData = new FormData();

      formData.append("file", file);

      const response = await fetch(
        `${API_BASE_URL}/api/v1/datasets/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to upload dataset."
        );
      }

      setDataset(data);

    } catch (err) {
      setError(
        err.message ||
          "Something went wrong while uploading."
      );
    } finally {
      setUploading(false);
    }
  };


  // --------------------------------------------------
  // ASK QUESTION
  // --------------------------------------------------

  const askQuestion = async () => {
    if (!dataset?.dataset?.dataset_id) {
      setError("Please upload a dataset first.");
      return;
    }

    if (!question.trim()) {
      setError("Please enter a question.");
      return;
    }

    setAsking(true);
    setError("");
    setAnswer(null);

    try {
      const datasetId =
        dataset.dataset.dataset_id;

      const response = await fetch(
        `${API_BASE_URL}/api/v1/analysis/${datasetId}/ask`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: question.trim(),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Failed to analyze the dataset."
        );
      }

      setAnswer(data);

    } catch (err) {
      setError(
        err.message ||
          "Something went wrong while analyzing."
      );
    } finally {
      setAsking(false);
    }
  };


  // --------------------------------------------------
  // REMOVE FILE
  // --------------------------------------------------

  const removeFile = () => {
    setFile(null);
    setDataset(null);
    setAnswer(null);
    setQuestion("");
    setError("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };


  // --------------------------------------------------
  // EXAMPLE QUESTIONS
  // --------------------------------------------------

  const exampleQuestions = [
    "How many rows are in this dataset?",
    "What are the main columns?",
    "Give me a summary of this dataset.",
    "What is the average value of the numeric data?",
  ];


  return (
    <div className="app-shell">

      {/* --------------------------------------------- */}
      {/* BACKGROUND */}
      {/* --------------------------------------------- */}

      <div className="background-glow glow-one"></div>
      <div className="background-glow glow-two"></div>


      {/* --------------------------------------------- */}
      {/* NAVBAR */}
      {/* --------------------------------------------- */}

      <header className="navbar">

        <div className="brand">
          <div className="brand-icon">
            <BarChart3 size={22} />
          </div>

          <span>InsightX</span>
        </div>

        <div className="navbar-tag">
          <Sparkles size={15} />
          AI Dataset Analyst
        </div>

      </header>


      {/* --------------------------------------------- */}
      {/* MAIN */}
      {/* --------------------------------------------- */}

      <main className="main-container">

        {/* HERO */}

        <section className="hero-section">

          <div className="hero-badge">
            <Sparkles size={15} />
            Chat with your data
          </div>

          <h1>
            Understand your dataset
            <span> with AI.</span>
          </h1>

          <p>
            Upload a CSV or Excel file, ask questions
            in plain English, and get clear answers
            from your own data.
          </p>

        </section>


        {/* ------------------------------------------- */}
        {/* UPLOAD CARD */}
        {/* ------------------------------------------- */}

        <section className="upload-card">

          <div className="section-heading">

            <div className="section-icon">
              <Database size={20} />
            </div>

            <div>
              <h2>Upload your dataset</h2>

              <p>
                CSV or XLSX files are supported
              </p>
            </div>

          </div>


          {!file ? (

            <div
              className={`drop-zone ${
                dragActive ? "drag-active" : ""
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() =>
                fileInputRef.current?.click()
              }
            >

              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx"
                onChange={handleFileInput}
                hidden
              />

              <div className="upload-icon">
                <Upload size={28} />
              </div>

              <h3>
                Drop your dataset here
              </h3>

              <p>
                or click to browse from your computer
              </p>

              <span className="file-types">
                CSV • XLSX
              </span>

            </div>

          ) : (

            <div className="selected-file">

              <div className="file-icon">
                <FileSpreadsheet size={24} />
              </div>

              <div className="file-info">

                <strong>
                  {file.name}
                </strong>

                <span>
                  {(file.size / 1024).toFixed(1)} KB
                </span>

              </div>

              <button
                className="icon-button"
                onClick={removeFile}
              >
                <X size={18} />
              </button>

            </div>

          )}


          {file && !dataset && (

            <button
              className="primary-button upload-button"
              onClick={uploadDataset}
              disabled={uploading}
            >

              {uploading ? (
                <>
                  <Loader2
                    size={18}
                    className="spin"
                  />
                  Processing dataset...
                </>
              ) : (
                <>
                  <Upload size={18} />
                  Analyze dataset
                </>
              )}

            </button>

          )}


          {dataset && (

            <div className="success-box">

              <CheckCircle2 size={20} />

              <div>

                <strong>
                  Dataset ready
                </strong>

                <span>
                  {dataset.profile?.row_count} rows
                  {" • "}
                  {dataset.profile?.column_count} columns
                </span>

              </div>

            </div>

          )}

        </section>


        {/* ------------------------------------------- */}
        {/* QUESTION SECTION */}
        {/* ------------------------------------------- */}

        {dataset && (

          <section className="question-card">

            <div className="section-heading">

              <div className="section-icon ai-icon">
                <Sparkles size={20} />
              </div>

              <div>

                <h2>
                  Ask your dataset
                </h2>

                <p>
                  Ask anything about the data in
                  natural language.
                </p>

              </div>

            </div>


            {/* QUESTION INPUT */}

            <div className="question-input-wrapper">

              <textarea
                value={question}
                onChange={(event) =>
                  setQuestion(event.target.value)
                }
                placeholder="e.g. What is the average value in this dataset?"
                rows={3}
                onKeyDown={(event) => {

                  if (
                    event.key === "Enter" &&
                    !event.shiftKey
                  ) {
                    event.preventDefault();
                    askQuestion();
                  }

                }}
              />

              <button
                className="ask-button"
                onClick={askQuestion}
                disabled={asking || !question.trim()}
              >

                {asking ? (
                  <Loader2
                    size={19}
                    className="spin"
                  />
                ) : (
                  <Send size={19} />
                )}

                {asking
                  ? "Analyzing..."
                  : "Ask"}

              </button>

            </div>


            {/* EXAMPLES */}

            <div className="examples">

              <span>
                Try asking:
              </span>

              <div className="example-list">

                {exampleQuestions.map(
                  (example) => (

                    <button
                      key={example}
                      onClick={() =>
                        setQuestion(example)
                      }
                    >
                      {example}
                    </button>

                  )
                )}

              </div>

            </div>


            {/* --------------------------------------- */}
            {/* ANSWER */}
            {/* --------------------------------------- */}

            {answer && (

              <div className="answer-card">

                <div className="answer-header">

                  <div className="answer-title">

                    <div className="answer-icon">
                      <Sparkles size={17} />
                    </div>

                    <span>
                      InsightX Answer
                    </span>

                  </div>

                </div>


                <div className="answer-content">

                  {answer.answer}

                </div>


                <div className="answer-meta">

                  <span>
                    Based on{" "}
                    {answer.rows_analyzed} rows
                  </span>

                  <span className="dot">
                    •
                  </span>

                  <span>
                    {answer.dataset_name}
                  </span>

                </div>

              </div>

            )}

          </section>

        )}


        {/* ------------------------------------------- */}
        {/* ERROR */}
        {/* ------------------------------------------- */}

        {error && (

          <div className="error-box">

            <X size={18} />

            <span>
              {error}
            </span>

          </div>

        )}


        {/* ------------------------------------------- */}
        {/* FOOTER */}
        {/* ------------------------------------------- */}

        <footer>

          <span>
            InsightX
          </span>

          <span>
            AI-powered dataset analysis
          </span>

        </footer>

      </main>

    </div>
  );
}


export default App;