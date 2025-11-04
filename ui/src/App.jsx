import { useEffect, useMemo, useState } from "react";

const siteOptions = [
  { value: "tricore", label: "TriCore" },
  { value: "xr", label: "XR" },
  { value: "quest", label: "Quest" },
  { value: "zio", label: "Zio" },
];

const genderOptions = [
  { value: "", label: "Unspecified" },
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
];

const initialForm = {
  site: "tricore",
  firstName: "",
  lastName: "",
  dob: "",
  gender: "",
  startDate: "",
  endDate: "",
};

const DEFAULT_API_BASE = "http://18.209.212.250:8080";

function normalizeBaseUrl(value) {
  const trimmed = (value ?? "").trim();
  if (!trimmed) {
    return DEFAULT_API_BASE;
  }
  return trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
}

const apiBaseUrl = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL);

function formatDob(value) {
  const trimmed = (value || "").trim();
  if (!trimmed) {
    return "";
  }
  const parts = trimmed.split("-");
  if (parts.length === 3) {
    const [year, month, day] = parts;
    return `${month}${day}${year}`;
  }
  const digits = trimmed.replace(/[^0-9]/g, "");
  if (digits.length === 8) {
    const month = digits.slice(0, 2);
    const day = digits.slice(2, 4);
    const year = digits.slice(4);
    return `${month}${day}${year}`;
  }
  return digits;
}

function formatDayMonthYear(value) {
  const trimmed = (value || "").trim();
  if (!trimmed) {
    return "";
  }
  const parts = trimmed.split("-");
  if (parts.length === 3) {
    const [year, month, day] = parts;
    return `${month}${day}${year}`;
  }
  const digits = trimmed.replace(/[^0-9]/g, "");
  if (digits.length === 8) {
    const month = digits.slice(0, 2);
    const day = digits.slice(2, 4);
    const year = digits.slice(4);
    return `${month}${day}${year}`;
  }
  return digits;
}

function buildPayload(form) {
  const payload = {
    site: form.site,
    patient: {
      first_name: form.firstName.trim(),
      last_name: form.lastName.trim(),
    },
  };

  if (form.dob.trim()) {
    const formattedDob = formatDob(form.dob);
    payload.patient.dob = formattedDob;
  }

  const options = {};
  if (form.gender.trim() && form.site === "tricore") {
    options.gender = form.gender.trim();
  }
  if (form.startDate.trim()) {
    const formattedStart = formatDayMonthYear(form.startDate);
    options.start_date = formattedStart;
  }
  if (form.endDate.trim()) {
    const formattedEnd = formatDayMonthYear(form.endDate);
    options.end_date = formattedEnd;
  }

  if (Object.keys(options).length > 0) {
    payload.options = options;
  }

  return payload;
}

function validate(form) {
  const missing = [];
  if (!form.firstName.trim()) {
    missing.push("First name is required");
  }
  if (!form.lastName.trim()) {
    missing.push("Last name is required");
  }

  if (form.site === "tricore") {
    if (!form.dob.trim()) {
      missing.push("Date of birth is required for TriCore");
    }
    if (!form.gender.trim()) {
      missing.push("Gender is required for TriCore");
    }
  }

  if (form.site === "quest" && !form.dob.trim()) {
    missing.push("Date of birth is required for Quest");
  }

  if (form.site === "xr") {
    const hasStart = Boolean(form.startDate.trim());
    const hasEnd = Boolean(form.endDate.trim());
    if (hasStart !== hasEnd) {
      missing.push("XR requires both start and end dates when filtering by date");
    }
  }

  return missing;
}

export default function App() {
  const [form, setForm] = useState(initialForm);
  const [dobPicker, setDobPicker] = useState("");
  const [startPicker, setStartPicker] = useState("");
  const [endPicker, setEndPicker] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);

  useEffect(() => {
    if (form.site !== "tricore" && form.gender) {
      setForm((prev) => ({
        ...prev,
        gender: "",
      }));
    }
  }, [form.site, form.gender]);

  const patientLabel = useMemo(() => {
    if (!result?.patient_name) {
      return "";
    }
    return `${result.patient_name} · ${result.report_date}`;
  }, [result]);

  function handleChange(event) {
    const { name, value } = event.target;
    if (name === "dob") {
      setDobPicker(value);
      setForm((prev) => ({
        ...prev,
        dob: formatDob(value),
      }));
      return;
    }
    if (name === "startDate") {
      setStartPicker(value);
      setForm((prev) => ({
        ...prev,
        startDate: formatDayMonthYear(value),
      }));
      return;
    }
    if (name === "endDate") {
      setEndPicker(value);
      setForm((prev) => ({
        ...prev,
        endDate: formatDayMonthYear(value),
      }));
      return;
    }
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setResult(null);
    setJobId(null);
    setJobStatus(null);

    const issues = validate(form);
    if (issues.length > 0) {
      setError(issues.join(". "));
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = buildPayload(form);
      const response = await fetch(`${apiBaseUrl}/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const details = await response.json().catch(() => ({}));
        throw new Error(details.detail || `Request failed with status ${response.status}`);
      }

      const job = await response.json();
      setJobId(job.job_id);
      setJobStatus(job.status || "pending");
    } catch (submitError) {
      setError(submitError.message || "Unexpected error occurred");
      setIsSubmitting(false);
    }
  }

  function handleReset() {
    setForm(initialForm);
    setDobPicker("");
    setStartPicker("");
    setEndPicker("");
    setError("");
    setResult(null);
    setJobId(null);
    setJobStatus(null);
    setIsSubmitting(false);
  }

  useEffect(() => {
    if (!jobId) {
      return undefined;
    }

    let cancelled = false;
    let finished = false;
    let intervalId = null;

    const pollStatus = async () => {
      if (cancelled || finished) {
        return;
      }

      try {
        const response = await fetch(`${apiBaseUrl}/jobs/${jobId}`);
        if (!response.ok) {
          const details = await response.json().catch(() => ({}));
          throw new Error(details.detail || `Job status request failed with status ${response.status}`);
        }

        const data = await response.json();
        if (cancelled) {
          return;
        }

        setJobStatus(data.status);
        if (data.status === "completed") {
          setResult(data.result || null);
          setIsSubmitting(false);
          finished = true;
          if (intervalId) {
            clearInterval(intervalId);
          }
        } else if (data.status === "failed") {
          setError(data.error || "Automation job failed");
          setIsSubmitting(false);
          finished = true;
          if (intervalId) {
            clearInterval(intervalId);
          }
        }
      } catch (pollError) {
        if (!cancelled) {
          setError(pollError.message || "Unable to fetch job status");
          setIsSubmitting(false);
          finished = true;
          if (intervalId) {
            clearInterval(intervalId);
          }
        }
      }
    };

    pollStatus();
    intervalId = setInterval(pollStatus, 4000);

    return () => {
      cancelled = true;
      finished = true;
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [apiBaseUrl, jobId]);

  const isWaitingForResult =
    isSubmitting && jobId && jobStatus && !["completed", "failed"].includes(jobStatus);

  return (
    <div className="page">
      <header className="page__header">
        <h1>Medical Report Retrieval</h1>
        <p className="page__subtitle">Trigger automations and review generated reports in one place.</p>
      </header>

      <section className="card">
        <form className="form" onSubmit={handleSubmit}>
          <div className="form__grid">
            <label className="form__field">
              <span>Site</span>
              <select name="site" value={form.site} onChange={handleChange}>
                {siteOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="form__field">
              <span>First Name</span>
              <input
                name="firstName"
                type="text"
                value={form.firstName}
                onChange={handleChange}
                placeholder="Jane"
              />
            </label>

            <label className="form__field">
              <span>Last Name</span>
              <input
                name="lastName"
                type="text"
                value={form.lastName}
                onChange={handleChange}
                placeholder="Doe"
              />
            </label>

            <label className="form__field">
              <span>Date of Birth</span>
              <input
                name="dob"
                type="date"
                placeholder="MM/DD/YYYY"
                value={dobPicker}
                onChange={handleChange}
              />
            </label>

            <label className="form__field">
              <span>Gender</span>
              <select
                name="gender"
                value={form.gender}
                onChange={handleChange}
                disabled={form.site !== "tricore"}
              >
                {genderOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="form__field">
              <span>Start Date</span>
              <input
                name="startDate"
                type="date"
                placeholder="MM/DD/YYYY"
                value={startPicker}
                onChange={handleChange}
              />
            </label>

            <label className="form__field">
              <span>End Date</span>
              <input
                name="endDate"
                type="date"
                placeholder="MM/DD/YYYY"
                value={endPicker}
                onChange={handleChange}
              />
            </label>
          </div>

          <div className="form__actions">
            <button type="submit" className="button button--primary" disabled={isSubmitting}>
              {isSubmitting ? "Running..." : "Run Automation"}
            </button>
            <button type="button" className="button" onClick={handleReset} disabled={isSubmitting}>
              Reset
            </button>
          </div>
        </form>

        {jobId ? (
          <div className="status status--info">
            <strong>Job ID:</strong> <code>{jobId}</code> · Status: {jobStatus || "pending"}
          </div>
        ) : null}

        {error ? <div className="alert alert--error">{error}</div> : null}
      </section>

      <section className="card">
        <header className="card__header">
          <h2>Generated Reports</h2>
          {patientLabel ? <span className="card__meta">{patientLabel}</span> : null}
        </header>

        {isWaitingForResult ? <p className="status">Automation is running...</p> : null}

        {result && result.patient_files?.length > 0 ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Report</th>
                  <th>Open in S3</th>
                  <th>Download</th>
                </tr>
              </thead>
              <tbody>
                {result.patient_files.map((file) => (
                  <tr key={file.s3_file_url}>
                    <td>{file.s3_file_name}</td>
                    <td>
                      <a href={file.s3_console_url} target="_blank" rel="noopener noreferrer">
                        View
                      </a>
                    </td>
                    <td>
                      <a href={file.s3_file_download} target="_blank" rel="noopener noreferrer">
                        Download
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="status">No reports yet. Run an automation to populate this table.</p>
        )}
      </section>
    </div>
  );
}
