import { useCallback, useEffect, useRef, useState } from "react";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

const SITE_RUN_ORDER = ["tricore", "xr", "quest", "zio"];
const SITE_LABELS = {
  tricore: "TRICORE",
  xr: "XRAYNM",
  quest: "QUEST",
  zio: "ZIOSUITE",
};

const siteOptions = [
  { value: "tricore", label: SITE_LABELS.tricore },
  { value: "xr", label: SITE_LABELS.xr },
  { value: "quest", label: SITE_LABELS.quest },
  { value: "zio", label: SITE_LABELS.zio },
  { value: "all", label: "ALL" },
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

const FINAL_JOB_STATUSES = new Set(["completed", "failed"]);

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

function buildPayload(form, startDateValue, endDateValue, siteOverride = form.site) {
  const payload = {
    site: siteOverride,
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
  if (form.gender.trim() && siteOverride === "tricore") {
    options.gender = form.gender.trim();
  }
  if (siteOverride === "xr" && startDateValue.trim()) {
    const formattedStart = formatDayMonthYear(startDateValue);
    options.start_date = formattedStart;
  }
  if (siteOverride === "xr" && endDateValue.trim()) {
    const formattedEnd = formatDayMonthYear(endDateValue);
    options.end_date = formattedEnd;
  }

  if (Object.keys(options).length > 0) {
    payload.options = options;
  }

  return payload;
}

function validate(form, startDateValue, endDateValue, siteContext = form.site) {
  const missing = [];
  const siteKey = siteContext || form.site;
  const siteLabel = SITE_LABELS[siteKey] || siteKey.toUpperCase();

  if (!form.firstName.trim()) {
    missing.push("First name is required");
  }
  if (!form.lastName.trim()) {
    missing.push("Last name is required");
  }

  if (siteKey === "tricore") {
    if (!form.dob.trim()) {
      missing.push(`[${siteLabel}] Date of birth is required.`);
    }
    if (!form.gender.trim()) {
      missing.push(`[${siteLabel}] Gender is required.`);
    }
  }

  if (siteKey === "quest" && !form.dob.trim()) {
    missing.push(`[${siteLabel}] Date of birth is required.`);
  }

  if (siteKey === "xr") {
    const hasStart = Boolean(startDateValue.trim());
    const hasEnd = Boolean(endDateValue.trim());
    if (hasStart !== hasEnd) {
      missing.push(`[${siteLabel}] Start and end dates must both be provided.`);
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
  const [activeSites, setActiveSites] = useState([initialForm.site]);
  const [siteJobs, setSiteJobs] = useState({});
  const siteJobsRef = useRef(siteJobs);
  const [resultsBySite, setResultsBySite] = useState({});
  const [siteErrors, setSiteErrors] = useState({});
  const [expandedSites, setExpandedSites] = useState(() =>
    SITE_RUN_ORDER.reduce((acc, site) => ({ ...acc, [site]: true }), {})
  );
  const jobsPollerRef = useRef(null);
  const [logs, setLogs] = useState([]);
  const [isLogPanelOpen, setIsLogPanelOpen] = useState(false);
  const [isFetchingLogs, setIsFetchingLogs] = useState(false);
  const [logError, setLogError] = useState("");
  const logListRef = useRef(null);
  const [isSiteLocked, setIsSiteLocked] = useState(false);

  const selectedSites = activeSites.length ? activeSites : [initialForm.site];
  const runsTricore = selectedSites.includes("tricore");
  const runsXr = selectedSites.includes("xr");
  const runsZioOnly = selectedSites.length === 1 && selectedSites[0] === "zio";

  useEffect(() => {
    siteJobsRef.current = siteJobs;
  }, [siteJobs]);

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
      if (!isoValue && runsXr) {
        setStartPicker("");
      }
    },
    [runsXr]
  );

  const stopPolling = useCallback(() => {
    if (jobsPollerRef.current) {
      clearInterval(jobsPollerRef.current);
      jobsPollerRef.current = null;
    }
  }, []);

  const fetchBackendLogs = useCallback(async () => {
    setIsFetchingLogs(true);
    try {
      const response = await fetch(`${apiBaseUrl}/logs?limit=200`);
      if (!response.ok) {
        const details = await response.json().catch(() => ({}));
        throw new Error(details.detail || "Unable to load logs");
      }
      const data = await response.json();
      setLogs(data.logs || []);
      setLogError("");
    } catch (fetchError) {
      setLogError(fetchError.message || "Unable to load logs");
    } finally {
      setIsFetchingLogs(false);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    if (!isLogPanelOpen) {
      return undefined;
    }
    fetchBackendLogs();
    const interval = setInterval(() => {
      fetchBackendLogs();
    }, 5000);
    return () => {
      clearInterval(interval);
    };
  }, [isLogPanelOpen, fetchBackendLogs]);

  useEffect(() => {
    if (!logs.length || !logListRef.current) {
      return;
    }
    logListRef.current.scrollTop = logListRef.current.scrollHeight;
  }, [logs]);
  const handleSiteSelect = useCallback(
    (value) => {
      if (isSiteLocked) {
        return;
      }
      setForm((prev) => {
        if (prev.site === value) {
          return prev;
        }
        return {
          ...prev,
          site: value,
          period: value === "xr" || value === "all" ? prev.period || "1_month" : "",
        };
      });
      setActiveSites(value === "all" ? [...SITE_RUN_ORDER] : [value]);
    },
    [isSiteLocked]
  );

  useEffect(() => {
    if (!runsTricore && form.gender) {
      setForm((prev) => ({
        ...prev,
        gender: "",
      }));
    }
  }, [runsTricore, form.gender]);

  useEffect(() => {
    if (!runsXr) {
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
  }, [runsXr, endPicker, form.period]);

  useEffect(() => {
    if (!runsXr || !form.period || !endPicker) {
      return;
    }
    const computed = getStartDateForPeriod(endPicker, form.period);
    if (!computed) {
      setStartPicker("");
      return;
    }
    setStartPicker((prev) => (prev === computed ? prev : computed));
  }, [runsXr, form.period, endPicker]);

  const onlyZioSelected = runsZioOnly;

  function handleChange(event) {
    const { name, value } = event.target;
    if (name === "period") {
      setForm((prev) => ({
        ...prev,
        period: value,
      }));
      if (runsXr && !value) {
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
    stopPolling();
    setError("");
    setSiteErrors({});
    setResultsBySite({});
    setSiteJobs({});
    siteJobsRef.current = {};

    const targetSites = [...selectedSites];
    if (!targetSites.length) {
      setError("Select at least one site to run.");
      return;
    }

    const issues = [...new Set(targetSites.flatMap((site) => validate(form, startPicker, endPicker, site)))];
    if (issues.length > 0) {
      setError(issues.join(" "));
      return;
    }

    setIsSiteLocked(true);
    setIsSubmitting(true);

    const jobMap = {};
    const errorMap = {};

    await Promise.all(
      targetSites.map(async (site) => {
        try {
          const payload = buildPayload(form, startPicker, endPicker, site);
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
          jobMap[site] = {
            jobId: job.job_id,
            status: job.status || "pending",
          };
        } catch (submitError) {
          errorMap[site] = submitError.message || "Unable to start automation";
        }
      })
    );

    setSiteJobs(jobMap);
    siteJobsRef.current = jobMap;
    setSiteErrors(errorMap);

    if (Object.keys(jobMap).length === 0) {
      setIsSubmitting(false);
      setIsSiteLocked(false);
      setError(
        Object.keys(errorMap).length
          ? "Unable to start automation for the selected sites. See details below."
          : "Unable to start automation."
      );
      return;
    }

    setResultsBySite({});
    setError(Object.keys(errorMap).length ? "Some sites failed to start. See details below." : "");
    setExpandedSites((prev) => {
      const next = { ...prev };
      targetSites.forEach((site) => {
        next[site] = true;
      });
      return next;
    });
    startPolling();
  }

  function handleReset() {
    setForm(initialForm);
    setDobPicker("");
    setStartPicker("");
    setEndPicker("");
    stopPolling();
    setError("");
    setSiteJobs({});
    siteJobsRef.current = {};
    setSiteErrors({});
    setResultsBySite({});
    setIsSubmitting(false);
    setIsSiteLocked(false);
    setActiveSites([initialForm.site]);
    setExpandedSites(SITE_RUN_ORDER.reduce((acc, site) => ({ ...acc, [site]: true }), {}));
  }

  const fetchJobsStatus = useCallback(async () => {
    const snapshot = siteJobsRef.current;
    const entries = Object.entries(snapshot).filter(([, job]) => job?.jobId);
    if (!entries.length) {
      stopPolling();
      setIsSubmitting(false);
      setIsSiteLocked(false);
      return;
    }

    await Promise.all(
      entries.map(async ([site, job]) => {
        if (!job || FINAL_JOB_STATUSES.has(job.status)) {
          return;
        }
        try {
          const response = await fetch(`${apiBaseUrl}/jobs/${job.jobId}`);
          if (!response.ok) {
            const details = await response.json().catch(() => ({}));
            throw new Error(details.detail || `Job status request failed with status ${response.status}`);
          }
          const data = await response.json();
          setSiteJobs((prev) => ({
            ...prev,
            [site]: {
              ...prev[site],
              status: data.status,
            },
          }));
          if (data.status === "completed") {
            setResultsBySite((prev) => ({
              ...prev,
              [site]: data.result || null,
            }));
            setSiteErrors((prev) => {
              const { [site]: _ignored, ...rest } = prev;
              return rest;
            });
          } else if (data.status === "failed") {
            setSiteErrors((prev) => ({
              ...prev,
              [site]: data.error || "Automation job failed",
            }));
          }
        } catch (pollError) {
          setSiteErrors((prev) => ({
            ...prev,
            [site]: pollError.message || "Unable to fetch job status",
          }));
          setSiteJobs((prev) => ({
            ...prev,
            [site]: {
              ...prev[site],
              status: "failed",
            },
          }));
        }
      })
    );

    const updatedJobs = siteJobsRef.current;
    const allFinished = Object.values(updatedJobs).every(
      (job) => !job?.jobId || FINAL_JOB_STATUSES.has(job.status)
    );
    if (allFinished) {
      stopPolling();
      setIsSubmitting(false);
      setIsSiteLocked(false);
    }
  }, [apiBaseUrl, stopPolling]);

  const startPolling = useCallback(() => {
    fetchJobsStatus();
    if (!jobsPollerRef.current) {
      jobsPollerRef.current = setInterval(() => {
        fetchJobsStatus();
      }, 4000);
    }
  }, [fetchJobsStatus]);

  useEffect(
    () => () => {
      stopPolling();
    },
    [stopPolling]
  );

  const hasActiveJobs = Object.values(siteJobs).some(
    (job) => job?.jobId && !FINAL_JOB_STATUSES.has(job.status)
  );
  const isWaitingForResult = isSubmitting && hasActiveJobs;
  const visibleSiteKeys = SITE_RUN_ORDER.filter(
    (site) => siteJobs[site] || resultsBySite[site] || siteErrors[site]
  );
  const hasSiteData = visibleSiteKeys.length > 0;

  const handleToggleSite = useCallback((site) => {
    setExpandedSites((prev) => ({
      ...prev,
      [site]: !prev[site],
    }));
  }, []);

  const handleRefreshStatuses = useCallback(() => {
    fetchJobsStatus();
  }, [fetchJobsStatus]);

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
                  const disabled = isSiteLocked || isSubmitting;
                  return (
                    <label
                      key={option.value}
                      className={`site-checkbox ${checked ? "site-checkbox--active" : ""} ${
                        disabled && !checked ? "site-checkbox--disabled" : ""
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => handleSiteSelect(option.value)}
                        disabled={isSiteLocked || isSubmitting}
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
                  {onlyZioSelected ? <span className="form__note form__note--inline">Not required</span> : null}
                </div>
                <div className="dob-row">
                  <DatePicker
                    selected={fromISODate(dobPicker)}
                    onChange={handleDobDateChange}
                    placeholderText="MM/DD/YYYY"
                    dateFormat="MM/dd/yyyy"
                    isClearable
                    className="date-input"
                    disabled={onlyZioSelected}
                  />
                </div>
              </label>

              <label className="form__field">
                <div className="form__label-row">
                  <span>Gender</span>
                  {!runsTricore ? (
                    <span className="form__note form__note--inline">Not required</span>
                  ) : null}
                </div>
                <select
                  name="gender"
                  value={form.gender}
                  onChange={handleChange}
                  disabled={!runsTricore}
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
                  {!runsXr ? <span className="form__note form__note--inline">Not required</span> : null}
                </div>
                <select name="period" value={form.period} onChange={handleChange} disabled={!runsXr}>
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
                  {!runsXr ? <span className="form__note form__note--inline">Not required</span> : null}
                </div>
                <DatePicker
                  selected={fromISODate(startPicker)}
                  onChange={handleStartDateChange}
                  placeholderText="MM/DD/YYYY"
                  dateFormat="MM/dd/yyyy"
                  disabled={!runsXr}
                  className="date-input"
                />
              </label>

              <label className="form__field form__field--compact">
                <div className="form__label-row">
                  <span>To</span>
                  {!runsXr ? <span className="form__note form__note--inline">Not required</span> : null}
                </div>
                <DatePicker
                  selected={fromISODate(endPicker)}
                  onChange={handleEndDateChange}
                  placeholderText="MM/DD/YYYY"
                  dateFormat="MM/dd/yyyy"
                  disabled={!runsXr}
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
            <button
              type="button"
              className="button button--ghost"
              onClick={() => setIsLogPanelOpen(true)}
            >
              View Logs
            </button>
          </div>
        </form>

        {error ? <div className="alert alert--error">{error}</div> : null}
      </section>

      <section className="card card--stretch">
        <header className="card__header card__header--with-action">
          <div>
            <h2>Generated Reports</h2>
            {isWaitingForResult ? <span className="card__meta">Automation is running...</span> : null}
          </div>
          {hasActiveJobs ? (
            <button type="button" className="button button--ghost" onClick={handleRefreshStatuses}>
              Refresh Status
            </button>
          ) : null}
        </header>

        {hasSiteData ? (
          <div className="site-results">
            {visibleSiteKeys.map((site) => {
              const jobInfo = siteJobs[site];
              const result = resultsBySite[site];
              const siteError = siteErrors[site];
              const jobStatusLower = jobInfo?.status ? String(jobInfo.status).toLowerCase() : "";
              let statusKey = "idle";
              if (siteError) {
                statusKey = "failed";
              } else if (jobStatusLower) {
                statusKey = jobStatusLower;
              } else if (jobInfo?.jobId) {
                statusKey = "pending";
              }
              if (statusKey === "in_progress") {
                statusKey = "running";
              }
              const statusLabelMap = {
                idle: "Waiting",
                pending: "Pending",
                queued: "Queued",
                running: "Running",
                completed: "Completed",
                failed: "Failed",
              };
              const statusLabel = statusLabelMap[statusKey] || statusKey;

              return (
                <div key={site} className="site-result">
                  <button
                    type="button"
                    className="site-result__header"
                    onClick={() => handleToggleSite(site)}
                    aria-expanded={Boolean(expandedSites[site])}
                  >
                    <span className="site-result__title">{SITE_LABELS[site]}</span>
                    <span className={`site-result__status site-result__status--${statusKey}`}>
                      {statusLabel}
                    </span>
                  </button>
                  {expandedSites[site] ? (
                    <div className="site-result__body">
                      {jobInfo?.jobId ? (
                        <p className="status">
                          Job ID: <code>{jobInfo.jobId}</code> · Status: {jobInfo.status || "pending"}
                        </p>
                      ) : null}
                      {result?.patient_name ? (
                        <p className="status">
                          Patient: {result.patient_name}
                          {result.report_date ? ` · ${result.report_date}` : ""}
                        </p>
                      ) : null}

                      {result?.patient_files?.length ? (
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
                      ) : jobInfo && jobStatusLower === "completed" && !siteError ? (
                        <p className="status">No downloadable files returned.</p>
                      ) : !siteError ? (
                        <p className="status">Awaiting report generation...</p>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : (
          <p className="status">No reports yet. Run an automation to populate this table.</p>
        )}
      </section>

      {isLogPanelOpen ? (
        <button type="button" className="log-panel__backdrop" onClick={() => setIsLogPanelOpen(false)} aria-label="Close logs overlay" />
      ) : null}
      <aside className={`log-panel ${isLogPanelOpen ? "log-panel--open" : ""}`}>
        <div className="log-panel__header">
          <div>
            <h3>Automation Logs</h3>
            <p className="log-panel__meta">Latest events from backend loggers</p>
          </div>
          <div className="log-panel__actions">
            <button type="button" className="button button--ghost" onClick={fetchBackendLogs} disabled={isFetchingLogs}>
              {isFetchingLogs ? "Refreshing..." : "Refresh"}
            </button>
            <button type="button" className="button" onClick={() => setIsLogPanelOpen(false)}>
              Close
            </button>
          </div>
        </div>
        <div className="log-panel__body" ref={logListRef}>
          {logError ? <p className="log-error-message">{logError}</p> : null}
          {!logError && logs.length === 0 ? (
            <p className="log-empty">No logs yet. Run an automation to start capturing events.</p>
          ) : null}
          {logs.map((entry) => (
            <div key={`${entry.timestamp}-${entry.logger}-${entry.message}`} className={`log-entry log-entry--${entry.level}`}>
              <div className="log-entry__meta">
                <span className="log-entry__time">{entry.timestamp}</span>
                <span className="log-entry__logger">{entry.logger}</span>
              </div>
              <p className="log-entry__message">{entry.message}</p>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
