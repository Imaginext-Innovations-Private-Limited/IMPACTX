
const chart = new Chart(
    document.getElementById("cashChart"),
    {
        type: "bar",
        data: {
            labels: ["September", "October", "November"],
            datasets: [
                {
                    label: "Income",
                    data: [80000, 95000, 150000],
                    backgroundColor: "#259b78"
                },
                {
                    label: "Expenses",
                    data: [50000, 65000, 90000],
                    backgroundColor: "#e69b53"
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true
        }
    }
);


async function uploadDocument() {
    const file = document.getElementById("document").files[0];
    const type = document.getElementById("document-type").value;
    const status = document.getElementById("upload-status");

    if (!file) {
        status.textContent = "Please select a document.";
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", type);

    status.textContent = "Uploading...";

    try {
        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Upload failed");
        }

        status.textContent = result.message;

        // Automatically analyze bank statements
        if (type === "bank" && file.name.toLowerCase().endsWith(".csv")) {
            status.textContent = "Analyzing bank statement...";

            const analysisResponse = await fetch(
                "/api/process-bank-statement",
                { method: "POST" }
            );

            const analysis = await analysisResponse.json();

            if (!analysisResponse.ok) {
                throw new Error(analysis.detail || "Analysis failed");
            }

            status.textContent =
                `Analysis complete! Revenue: ₹${analysis.revenue.toLocaleString("en-IN")}, Expenses: ₹${analysis.expenses.toLocaleString("en-IN")}, Profit: ₹${analysis.profit.toLocaleString("en-IN")}`;

            await loadDashboard();
        }

    } catch (error) {
        status.textContent = "Error: " + error.message;
    }
}


async function sendMessage() {
    const input = document.getElementById("user-message");
    const chatBox = document.getElementById("chat-box");

    const message = input.value.trim();

    if (!message) return;

    chatBox.innerHTML += `
        <div class="user-message">${escapeHTML(message)}</div>
    `;

    input.value = "";

    const loading = document.createElement("div");
    loading.className = "bot-message";
    loading.textContent = "Thinking...";
    chatBox.appendChild(loading);

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({message})
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Chat failed");
        }

        loading.textContent = result.reply;
    } catch (error) {
        loading.textContent = "Assistant error: " + error.message;
    }

    chatBox.scrollTop = chatBox.scrollHeight;
}

function escapeHTML(value) {
    const element = document.createElement("div");
    element.textContent = value;
    return element.innerHTML;
}


async function loadDashboard() {
    try {
        const response = await fetch("/api/dashboard");
        const data = await response.json();

        document.getElementById("revenue").textContent =
            "₹" + data.revenue.toLocaleString("en-IN");

        document.getElementById("expenses").textContent =
            "₹" + data.expenses.toLocaleString("en-IN");

        document.getElementById("profit").textContent =
            "₹" + data.profit.toLocaleString("en-IN");

        document.getElementById("gst-count").textContent =
            data.gst_pending;

    } catch (error) {
        console.error("Dashboard error:", error);
    }
}

loadDashboard();


async function loadForecast() {
    try {
        const response = await fetch("/api/forecast");
        const data = await response.json();

        if (!data.forecast || data.forecast.length === 0) {
            document.getElementById("forecast-info").textContent =
                data.message || "No forecast available.";
            return;
        }

        document.getElementById("forecast-info").textContent =
            "Average Monthly Income: ₹" +
            data.average_income.toLocaleString("en-IN") +
            " | Average Monthly Expenses: ₹" +
            data.average_expenses.toLocaleString("en-IN");

        const ctx = document.getElementById("cashChart");

       const existingChart = Chart.getChart(ctx);

if (existingChart) {
    existingChart.destroy();
}

        window.forecastChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: data.forecast.map(item => item.month),
                datasets: [
                    {
                        label: "Expected Income",
                        data: data.forecast.map(item => item.income)
                    },
                    {
                        label: "Expected Expenses",
                        data: data.forecast.map(item => item.expenses)
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

    } catch (error) {
        console.error("Forecast error:", error);
    }
}

loadForecast();


async function loadGSTTasks() {
    try {
        const response = await fetch("/api/gst-tasks");
        const tasks = await response.json();

        const table = document.getElementById("gst-table");
        table.innerHTML = "";

        if (tasks.length === 0) {
            table.innerHTML =
                '<tr><td colspan="4">No GST tasks found.</td></tr>';
            return;
        }

        tasks.forEach(task => {
            const row = document.createElement("tr");

            row.innerHTML = `
                <td>${task.return_name}</td>
                <td>${task.due_date}</td>
                <td>${task.status}</td>
                <td>
                    ${task.status !== "Filed"
                        ? `<button onclick="markGSTFiled(${task.id})">Mark Filed</button>`
                        : "Completed"}
                </td>
            `;

            table.appendChild(row);
        });

    } catch (error) {
        console.error("GST loading error:", error);
    }
}

async function markGSTFiled(id) {
    const response = await fetch(`/api/gst-tasks/${id}/file`, {
        method: "PUT"
    });

    if (response.ok) {
        loadGSTTasks();
    }
}

loadGSTTasks();


async function addGSTTask() {
    const returnName = document.getElementById("gst-return-name").value;
    const dueDate = document.getElementById("gst-due-date").value;

    if (!dueDate) {
        alert("Please select a due date.");
        return;
    }

    try {
        const response = await fetch("/api/gst-tasks", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                return_name: returnName,
                due_date: dueDate
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Could not add GST task");
        }

        document.getElementById("gst-due-date").value = "";

        await loadGSTTasks();

        alert("GST task added successfully!");

    } catch (error) {
        alert(error.message);
    }
}



async function saveBusinessProfile() {
    const status = document.getElementById("profile-status");

    const getBoolean = (id) => {
        const value = document.getElementById(id).value;
        return value === "" ? null : value === "true";
    };

    const age = document.getElementById("applicant-age").value;

    const data = {
        business_name: document.getElementById("business-name").value.trim(),
        business_type: document.getElementById("business-type").value,
        annual_turnover: Number(document.getElementById("turnover").value),
        loan_requirement: Number(document.getElementById("loan-amount").value),
        business_age: Number(document.getElementById("business-age").value),
        employees: Number(document.getElementById("employees").value),

        applicant_age: age === "" ? null : Number(age),
        is_new_business: getBoolean("is-new-business"),
        education: document.getElementById("education").value || null,
        mudra_tarun_repaid: getBoolean("mudra-tarun-repaid"),
        udyam_registered: getBoolean("udyam-registered")
    };

    if (
        !data.business_name ||
        !data.business_type ||
        !document.getElementById("turnover").value ||
        !document.getElementById("loan-amount").value ||
        !document.getElementById("business-age").value ||
        !document.getElementById("employees").value
    ) {
        status.textContent = "Please complete all business details.";
        return;
    }

    try {
        status.textContent = "Saving business profile...";

        const response = await fetch("/api/business-profile", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Could not save profile");
        }

        status.textContent = "Business profile saved successfully!";

    } catch (error) {
        status.textContent = "Error: " + error.message;
    }
}



async function loadLoanRecommendations() {
    const results = document.getElementById("loan-results");
    const bestResult = document.getElementById("best-loan-result");

    results.innerHTML = "Finding suitable loan schemes...";
    bestResult.innerHTML = "";

    try {
        const response = await fetch("/api/loan-recommendations");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Could not load recommendations");
        }

        results.innerHTML = "";

        data.recommendations.forEach(item => {
            const card = document.createElement("div");
            card.className = "loan-card";

            card.innerHTML = `
                <h3>${item.scheme}</h3>
                <p><strong>Category:</strong> ${item.category}</p>
                <p>${item.reason}</p>
                <p><strong>Status:</strong> ${item.status}</p>
            `;

            results.appendChild(card);
        });

        const note = document.createElement("p");
        note.textContent = data.note;
        results.appendChild(note);

        // Display best loan suggestion
        if (data.best_option) {
            bestResult.innerHTML = `
                <div class="best-loan-card">
                    <h2>Best Loan Option for Your Business</h2>
                    <h3>${data.best_option.scheme}</h3>
                    <p>${data.best_option.reason}</p>
                    <p>${data.best_option.message}</p>
                </div>
            `;
        }

    } catch (error) {
        results.textContent = "Error: " + error.message;
        bestResult.textContent = "Error: " + error.message;
    }
}

async function logoutUser() {
    try {
        const response = await fetch("/api/logout", {
            method: "POST"
        });

        if (!response.ok) {
            throw new Error("Logout failed.");
        }

        window.location.href = "/";
    } catch (error) {
        alert(error.message);
    }
}

async function logoutUser() {
    try {
        const response = await fetch("/api/logout", {
            method: "POST"
        });

        if (!response.ok) {
            throw new Error("Logout failed");
        }

        window.location.replace("/login.html");
    } catch (error) {
        alert("Logout failed. Please try again.");
        console.error(error);
    }
}

function escapeHTML(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}

function renderList(items) {
    if (!Array.isArray(items) || items.length === 0) return "";
    return "<ul>" + items.map(i => `<li>${escapeHTML(i)}</li>`).join("") + "</ul>";
}

async function loadAILoanAdvice() {
    const box = document.getElementById("ai-loan-advice");
    box.innerHTML = "<p>MSME Mitra is analysing your profile and cash flow...</p>";

    try {
        const response = await fetch("/api/loan-advice", { method: "POST" });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Could not get AI loan advice");
        }

        if (!data.advice) {
            box.innerHTML = `<p>${escapeHTML(data.message)}</p>`;
            return;
        }

        const a = data.advice;
        const f = data.affordability;
        const s = data.financial_snapshot;

        const cashFlowLine = s.has_data
            ? `Avg monthly net cash flow: ₹${Number(s.avg_monthly_net_cash_flow).toLocaleString("en-IN")}`
            : "Upload a bank statement for a cash-flow based check.";

        box.innerHTML = `
            <div class="best-loan-card">
                <h2>AI Loan Advice ${data.ai_generated ? "" : "(basic mode)"}</h2>
                <p>${escapeHTML(a.summary)}</p>

                <h3>Recommended: ${escapeHTML(data.best_option.scheme)}</h3>
                <p>${escapeHTML(a.why_this_scheme)}</p>

                <h3>Can you afford it? (${escapeHTML(f.rating)})</h3>
                <p>Estimated EMI: ₹${Number(f.estimated_monthly_emi).toLocaleString("en-IN")}/month
                   (assumed ${f.assumed_interest_rate_percent}% for ${f.assumed_tenure_months / 12} years)</p>
                <p>${escapeHTML(cashFlowLine)}</p>
                <p>${escapeHTML(a.affordability_comment)}</p>

                <h3>Documents to keep ready</h3>
                ${renderList(a.documents_checklist)}

                <h3>Next steps</h3>
                ${renderList(a.next_steps)}

                <h3>Things to watch</h3>
                ${renderList(a.risks)}

                <p><small>${escapeHTML(data.disclaimer)}</small></p>
            </div>
        `;
    } catch (error) {
        box.textContent = "Error: " + error.message;
    }
}
