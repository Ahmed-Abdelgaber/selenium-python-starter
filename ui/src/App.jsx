import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

const siteOptions = [
  { value: "tricore", label: "TRICORE" },
  { value: "xr", label: "XRAYNM" },
  { value: "quest", label: "QUEST" },
  { value: "zio", label: "ZIOSUITE" },
];

const periodOptions = [
  { value: "1_week", label: "1 week" },
  { value: "1_month", label: "1 month" },
  { value: "3_months", label: "3 months" },
  { value: "6_months", label: "6 months" },
  { value: "1_year", label: "1 year" },
  { value: "2_years", label: "2 years" },
  { value: "3_years", label: "3 years" },
  { value: "5_years", label: "5 years" },
  { value: "10_years", label: "10 years" },
];

const genderOptions = [
  { value: "", label: "" },
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
];

const periodDurationsInDays = {
  "1_week": 7,
  "1_month": 30,
  "3_months": 90,
  "6_months": 182,
  "1_year": 365,
  "2_years": 730,
  "3_years": 1095,
  "5_years": 1825,
  "10_years": 3650,
};

const initialForm = {
  site: "tricore",
  firstName: "",
  lastName: "",
  dob: "",
  gender: "",
  period: "1_month",
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

function toISODate(date) {
  const tzOffset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - tzOffset).toISOString().slice(0, 10);
}

function addDaysToISODate(dateString, days) {
  if (!dateString) {
    return "";
  }
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  date.setDate(date.getDate() + days);
  return toISODate(date);
}

function getStartDateForPeriod(endDate, period) {
  const days = periodDurationsInDays[period];
  if (!days || !endDate) {
    return "";
  }
  return addDaysToISODate(endDate, -days);
}

function fromISODate(value) {
  if (!value) {
    return null;
  }
  const parts = value.split("-");
  if (parts.length !== 3) {
    return null;
  }
  const [year, month, day] = parts.map((part) => Number(part));
  if (!year || !month || !day) {
    return null;
  }
  const date = new Date(year, month - 1, day);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date;
}

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

function buildPayload(form, startDateValue, endDateValue) {
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
  if (form.site === "xr" && startDateValue.trim()) {
    const formattedStart = formatDayMonthYear(startDateValue);
    options.start_date = formattedStart;
  }
  if (form.site === "xr" && endDateValue.trim()) {
    const formattedEnd = formatDayMonthYear(endDateValue);
    options.end_date = formattedEnd;
  }

  if (Object.keys(options).length > 0) {
    payload.options = options;
  }

  return payload;
}

function validate(form, startDateValue, endDateValue) {
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
    const hasStart = Boolean(startDateValue.trim());
    const hasEnd = Boolean(endDateValue.trim());
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
  const pollerRef = useRef(null);

  const handleDobDateChange = useCallback((date) => {
    const isoValue = date ? toISODate(date) : "";
    setDobPicker(isoValue);
    setForm((prev) => ({
      ...prev,
      dob: formatDob(isoValue),
    }));
  }, []);

  const handleStartDateChange = useCallback((date) => {
    const isoValue = date ? toISODate(date) : "";
    setStartPicker(isoValue);
  }, []);

  const handleEndDateChange = useCallback(
    (date) => {
      const isoValue = date ? toISODate(date) : "";
      setEndPicker(isoValue);
      if (!isoValue && form.site === "xr") {
        setStartPicker("");
      }
    },
    [form.site]
  );

  const stopPolling = useCallback(() => {
    if (pollerRef.current) {
      clearInterval(pollerRef.current);
      pollerRef.current = null;
    }
  }, []);
  const handleSiteSelect = useCallback((value) => {
    setForm((prev) => {
      if (prev.site === value) {
        return prev;
      }
      return {
        ...prev,
        site: value,
        period: value === "xr" ? prev.period || "1_month" : "",
      };
    });
    setStartPicker("");
    setEndPicker("");
  }, []);

  useEffect(() => {
    if (form.site !== "tricore" && form.gender) {
      setForm((prev) => ({
        ...prev,
        gender: "",
      }));
    }
  }, [form.site, form.gender]);

  useEffect(() => {
    if (form.site !== "xr") {
      setStartPicker("");
      setEndPicker("");
      if (form.period) {
        setForm((prev) => ({
          ...prev,
          period: "",
        }));
      }
      return;
    }
    if (!endPicker) {
      setEndPicker(toISODate(new Date()));
    }
    if (!form.period) {
      setForm((prev) => ({
        ...prev,
        period: "1_month",
      }));
    }
  }, [form.site, endPicker, form.period]);

  useEffect(() => {
    if (form.site !== "xr" || !form.period || !endPicker) {
      return;
    }
    const computed = getStartDateForPeriod(endPicker, form.period);
    if (!computed) {
      setStartPicker("");
      return;
    }
    setStartPicker((prev) => (prev === computed ? prev : computed));
  }, [form.site, form.period, endPicker]);

  const patientLabel = useMemo(() => {
    if (!result?.patient_name) {
      return "";
    }
    return `${result.patient_name} · ${result.report_date}`;
  }, [result]);
  const isTricore = form.site === "tricore";
  const isXr = form.site === "xr";
  const isZio = form.site === "zio";

  useEffect(() => {
    if (!isZio) {
      return;
    }
    if (dobPicker || form.dob) {
      setDobPicker("");
      setForm((prev) => ({
        ...prev,
        dob: "",
      }));
    }
  }, [isZio, dobPicker, form.dob]);

  function handleChange(event) {
    const { name, value } = event.target;
    if (name === "period") {
      setForm((prev) => ({
        ...prev,
        period: value,
      }));
      if (form.site === "xr" && !value) {
        setStartPicker("");
      }
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
    stopPolling();

    const issues = validate(form, startPicker, endPicker);
    if (issues.length > 0) {
      setError(issues.join(". "));
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = buildPayload(form, startPicker, endPicker);
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
    stopPolling();
    setError("");
    setResult(null);
    setJobId(null);
    setJobStatus(null);
    setIsSubmitting(false);
  }

  const fetchJobStatus = useCallback(async () => {
    if (!jobId) {
      return;
    }
    try {
      const response = await fetch(`${apiBaseUrl}/jobs/${jobId}`);
      if (!response.ok) {
        const details = await response.json().catch(() => ({}));
        throw new Error(details.detail || `Job status request failed with status ${response.status}`);
      }
      const data = await response.json();
      setJobStatus(data.status);
      if (data.status === "completed") {
        setResult(data.result || null);
        setIsSubmitting(false);
        stopPolling();
      } else if (data.status === "failed") {
        setError(data.error || "Automation job failed");
        setIsSubmitting(false);
        stopPolling();
      }
    } catch (pollError) {
      setError(pollError.message || "Unable to fetch job status");
      setIsSubmitting(false);
      stopPolling();
    }
  }, [apiBaseUrl, jobId, stopPolling]);

  useEffect(() => {
    if (!jobId) {
      return undefined;
    }

    fetchJobStatus();
    if (!pollerRef.current) {
      pollerRef.current = setInterval(() => {
        fetchJobStatus();
      }, 4000);
    }

    return () => {
      stopPolling();
    };
  }, [jobId, fetchJobStatus, stopPolling]);

  const isWaitingForResult =
    isSubmitting && jobId && jobStatus && !["completed", "failed"].includes(jobStatus);

  return (
    <div className="page">
      <header className="page__header">
        <h1>Software Robot Automation</h1>
      </header>

      <section className="card card--stretch">
        <form className="form" onSubmit={handleSubmit}>
          <div className="filters-wrapper">
            <div className="filters-row filters-row--primary">
              <div className="form__field site-field" aria-label="Site selection">
                <span className="site-field__label">Select Site</span>
                <div className="site-checkboxes">
                  {siteOptions.map((option) => {
                    const checked = form.site === option.value;
                    return (
                      <label
                        key={option.value}
                        className={`site-checkbox ${checked ? "site-checkbox--active" : ""}`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => handleSiteSelect(option.value)}
                        />
                        <span className="site-checkbox__marker" />
                        <span className="site-checkbox__label">{option.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="filters-row filters-row--patient">
              <label className="form__field form__field--narrow">
                <span>Patient First Name</span>
                <input
                  name="firstName"
                  type="text"
                  value={form.firstName}
                  onChange={handleChange}
                  placeholder=""
                />
              </label>

              <label className="form__field form__field--narrow">
                <span>Patient Last Name</span>
                <input
                  name="lastName"
                  type="text"
                  value={form.lastName}
                  onChange={handleChange}
                  placeholder=""
                />
              </label>

              <label className="form__field dob-field">
                <div className="form__label-row">
                  <span>Date of Birth</span>
                  {isZio ? <span className="form__note form__note--inline">Not required</span> : null}
                </div>
                <div className="dob-row">
                  <DatePicker
                    selected={fromISODate(dobPicker)}
                    onChange={handleDobDateChange}
                    placeholderText="MM/DD/YYYY"
                    dateFormat="MM/dd/yyyy"
                    isClearable
                    className="date-input"
                    disabled={isZio}
                  />
                </div>
              </label>

              <label className="form__field">
                <div className="form__label-row">
                  <span>Gender</span>
                  {!isTricore ? (
                    <span className="form__note form__note--inline">Not required</span>
                  ) : null}
                </div>
                <select
                  name="gender"
                  value={form.gender}
                  onChange={handleChange}
                  disabled={!isTricore}
                >
                  {genderOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="filters-row filters-row--secondary">
              <label className="form__field form__field--compact">
                <div className="form__label-row">
                  <span>Time Period</span>
                  {!isXr ? <span className="form__note form__note--inline">Not required</span> : null}
                </div>
                <select name="period" value={form.period} onChange={handleChange} disabled={!isXr}>
                  <option value=""></option>
                  {periodOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form__field form__field--compact">
                <div className="form__label-row">
                  <span>From</span>
                  {!isXr ? <span className="form__note form__note--inline">Not required</span> : null}
                </div>
                <DatePicker
                  selected={fromISODate(startPicker)}
                  onChange={handleStartDateChange}
                  placeholderText="MM/DD/YYYY"
                  dateFormat="MM/dd/yyyy"
                  disabled={!isXr}
                  className="date-input"
                />
              </label>

              <label className="form__field form__field--compact">
                <div className="form__label-row">
                  <span>To</span>
                  {!isXr ? <span className="form__note form__note--inline">Not required</span> : null}
                </div>
                <DatePicker
                  selected={fromISODate(endPicker)}
                  onChange={handleEndDateChange}
                  placeholderText="MM/DD/YYYY"
                  dateFormat="MM/dd/yyyy"
                  disabled={!isXr}
                  className="date-input"
                />
              </label>
            </div>
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
            <button
              type="button"
              className="button"
              onClick={() => fetchJobStatus()}
              disabled={!jobId}
            >
              Refresh Status
            </button>
          </div>
        ) : null}

        {error ? <div className="alert alert--error">{error}</div> : null}
      </section>

      <section className="card card--stretch">
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
