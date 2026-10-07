document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const signupContainer = document.getElementById("signup-container");
  const messageDiv = document.getElementById("message");
  const accountToggle = document.getElementById("account-toggle");
  const accountMenu = document.getElementById("account-menu");
  const accountStatus = document.getElementById("account-status");
  const loginButton = document.getElementById("login-button");
  const logoutButton = document.getElementById("logout-button");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginError = document.getElementById("login-error");
  let isTeacher = false;

  function showMessage(text, className) {
    messageDiv.textContent = text;
    messageDiv.className = className;
    messageDiv.classList.remove("hidden");
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  function setTeacherState(authenticated, username) {
    isTeacher = authenticated;
    signupContainer.hidden = !authenticated;
    accountStatus.textContent = authenticated
      ? `Signed in as ${username}`
      : "Student view";
    loginButton.classList.toggle("hidden", authenticated);
    logoutButton.classList.toggle("hidden", !authenticated);
  }

  function makeTextElement(tagName, text, className) {
    const element = document.createElement(tagName);
    element.textContent = text;
    if (className) element.className = className;
    return element;
  }

  function createActivityCard(name, details) {
    const activityCard = document.createElement("div");
    activityCard.className = "activity-card";
    activityCard.append(makeTextElement("h4", name));
    activityCard.append(makeTextElement("p", details.description));

    const schedule = document.createElement("p");
    schedule.append(makeTextElement("strong", "Schedule: "));
    schedule.append(document.createTextNode(details.schedule));
    activityCard.append(schedule);

    const spotsLeft = details.max_participants - details.participants.length;
    const availability = document.createElement("p");
    availability.append(makeTextElement("strong", "Availability: "));
    availability.append(document.createTextNode(`${spotsLeft} spots left`));
    activityCard.append(availability);

    const participantsContainer = document.createElement("div");
    participantsContainer.className = "participants-container";
    const participantsSection = document.createElement("div");
    participantsSection.className = "participants-section";
    participantsSection.append(makeTextElement("h5", "Participants:"));

    if (details.participants.length) {
      const participantsList = document.createElement("ul");
      participantsList.className = "participants-list";
      details.participants.forEach((email) => {
        const participant = document.createElement("li");
        participant.append(makeTextElement("span", email, "participant-email"));
        if (isTeacher) {
          const deleteButton = makeTextElement("button", "Unregister", "delete-btn");
          deleteButton.type = "button";
          deleteButton.setAttribute("aria-label", `Unregister ${email} from ${name}`);
          deleteButton.dataset.activity = name;
          deleteButton.dataset.email = email;
          deleteButton.addEventListener("click", handleUnregister);
          participant.append(deleteButton);
        }
        participantsList.append(participant);
      });
      participantsSection.append(participantsList);
    } else {
      participantsSection.append(
        makeTextElement("p", "No participants yet")
      );
    }

    participantsContainer.append(participantsSection);
    activityCard.append(participantsContainer);
    return activityCard;
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) throw new Error("Failed to load activities");
      const activities = await response.json();
      activitiesList.replaceChildren();
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      Object.entries(activities).forEach(([name, details]) => {
        activitiesList.append(createActivityCard(name, details));
        activitySelect.append(new Option(name, name));
      });
    } catch (error) {
      activitiesList.replaceChildren(
        makeTextElement("p", "Failed to load activities. Please try again later.")
      );
      console.error("Error fetching activities:", error);
    }
  }

  async function refreshSession() {
    try {
      const response = await fetch("/auth/session");
      if (!response.ok) throw new Error("Failed to check teacher session");
      const session = await response.json();
      setTeacherState(session.authenticated, session.username);
      await fetchActivities();
    } catch (error) {
      setTeacherState(false, null);
      console.error("Error checking teacher session:", error);
      await fetchActivities();
    }
  }

  async function handleUnregister(event) {
    const button = event.currentTarget;
    const activity = button.dataset.activity;
    const email = button.dataset.email;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE" }
      );
      const result = await response.json();
      if (!response.ok) {
        if (response.status === 401) await refreshSession();
        showMessage(result.detail || "An error occurred", "error");
        return;
      }

      showMessage(result.message, "success");
      await fetchActivities();
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const activity = activitySelect.value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`,
        { method: "POST" }
      );
      const result = await response.json();
      if (!response.ok) {
        if (response.status === 401) await refreshSession();
        showMessage(result.detail || "An error occurred", "error");
        return;
      }

      showMessage(result.message, "success");
      signupForm.reset();
      await fetchActivities();
    } catch (error) {
      showMessage("Failed to register student. Please try again.", "error");
      console.error("Error registering student:", error);
    }
  });

  accountToggle.addEventListener("click", () => {
    const expanded = accountToggle.getAttribute("aria-expanded") === "true";
    accountToggle.setAttribute("aria-expanded", String(!expanded));
    accountMenu.classList.toggle("hidden", expanded);
  });

  loginButton.addEventListener("click", () => {
    accountMenu.classList.add("hidden");
    accountToggle.setAttribute("aria-expanded", "false");
    loginError.textContent = "";
    loginError.classList.add("hidden");
    loginDialog.showModal();
  });

  document.getElementById("close-login").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.textContent = "";
    loginError.classList.add("hidden");

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: document.getElementById("username").value,
          password: document.getElementById("password").value,
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Unable to log in");

      loginForm.reset();
      loginDialog.close();
      await refreshSession();
      showMessage("Teacher login successful.", "success");
    } catch (error) {
      loginError.textContent = error.message;
      loginError.classList.remove("hidden");
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "DELETE" });
      if (!response.ok) throw new Error("Unable to log out");
      setTeacherState(false, null);
      accountMenu.classList.add("hidden");
      accountToggle.setAttribute("aria-expanded", "false");
      await fetchActivities();
      showMessage("Logged out.", "success");
    } catch (error) {
      showMessage(error.message, "error");
      console.error("Error logging out:", error);
    }
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".account-controls")) {
      accountMenu.classList.add("hidden");
      accountToggle.setAttribute("aria-expanded", "false");
    }
  });

  refreshSession();
});
