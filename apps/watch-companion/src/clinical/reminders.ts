/**
 * Deterministic `PATIENT_FAMILY` Reminder Projector for Tier-0 Watch.
 *
 * Projects synced `VaccinationDueItem` records and open `PATIENT_FAMILY`
 * medication/care `ActionCard` items into glanceable, priority-ordered
 * watch reminders in English, pure *Shuddh Tatsama* Hindi, natural Kannada, and natural Tamil.
 */

import {
  ActionCard,
  ActionCardPriority,
  ActionCardStatus,
  VaccinationDueItem,
  VaccinationStatus,
} from "../../../../packages/contracts/ts/index";

export type WatchReminderCategory = "VACCINATION" | "MEDICATION" | "CARE";

export interface WatchReminderItem {
  id: string;
  category: WatchReminderCategory;
  priority: ActionCardPriority;
  status: VaccinationStatus | ActionCardStatus;
  dueBy: string | null;
  daysDelta: number | null;
  titleEn: string;
  titleHi: string;
  titleKn: string;
  titleTa: string;
  messageEn: string;
  messageHi: string;
  messageKn: string;
  messageTa: string;
  title: string;
  message: string;
  sourceCardId: string | null;
  vaccineCode: string | null;
}

export interface ReminderProjectionInput {
  vaccinations?: readonly VaccinationDueItem[];
  actionCards?: readonly ActionCard[];
  language?: "en" | "hi" | "kn" | "ta";
  includeUpcoming?: boolean;
  includeAcknowledged?: boolean;
}

const PRIORITY_RANK: Readonly<Record<ActionCardPriority, number>> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
};

const MEDICATION_KEYWORDS = [
  "medication",
  "medicine",
  "tablet",
  "syrup",
  "dose",
  "ors",
  "zinc",
  "ifa",
  "iron",
  "folic",
  "calcium",
  "paracetamol",
  "amoxicillin",
  "albendazole",
  "antibiotic",
  "औषधि",
  "ಔಷಧ",
  "ಮಾತ್ರೆ",
  "மருந்து",
  "மாத்திரை",
] as const;

function isMedicationActionCard(card: ActionCard): boolean {
  const haystack = [card.title, card.summary, ...card.action_steps]
    .join(" ")
    .toLowerCase();
  return MEDICATION_KEYWORDS.some((kw) => haystack.includes(kw));
}

function pickLocalized(
  language: "en" | "hi" | "kn" | "ta",
  enText: string,
  hiText: string,
  knText: string,
  taText: string,
): string {
  if (language === "hi") return hiText;
  if (language === "kn") return knText;
  if (language === "ta") return taText;
  return enText;
}

function formatVaccinationReminder(
  item: VaccinationDueItem,
  language: "en" | "hi" | "kn" | "ta",
  includeUpcoming: boolean,
): WatchReminderItem | null {
  if (item.status === "COMPLETED") {
    return null;
  }
  if (item.status === "UPCOMING" && !includeUpcoming) {
    return null;
  }

  let priority: ActionCardPriority;
  let titleEn: string;
  let titleHi: string;
  let titleKn: string;
  let titleTa: string;
  let messageEn: string;
  let messageHi: string;
  let messageKn: string;
  let messageTa: string;

  if (item.status === "OVERDUE") {
    const overdueDays = Math.abs(item.days_delta);
    priority = "HIGH";
    titleEn = `Overdue Vaccine: ${item.vaccine_name} (${item.dose_label})`;
    titleHi = `अतिदेय टीकाकरण: ${item.vaccine_name} (${item.dose_label})`;
    titleKn = `ತಡವಾದ ಲಸಿಕೆ: ${item.vaccine_name} (${item.dose_label})`;
    titleTa = `தாமதமான தடுப்பூசி: ${item.vaccine_name} (${item.dose_label})`;
    messageEn =
      item.reminder_text.trim().length > 0
        ? item.reminder_text
        : `Overdue by ${overdueDays} day(s) (due ${item.due_date}). Visit VHND/PHC with MCP Card.`;
    messageHi = `${overdueDays} दिवस अतिदेय (निर्धारित तिथि ${item.due_date})। मातृ-शिशु सुरक्षा पत्रक सहित निकटतम प्राथमिक स्वास्थ्य केंद्र पर जाएं।`;
    messageKn = `${overdueDays} ದಿನ ತಡವಾಗಿದೆ (ದಿನಾಂಕ ${item.due_date}). ತಾಯಿ-ಮಗು ಕಾರ್ಡ್ ತೆಗೆದುಕೊಂಡು ಆಸ್ಪತ್ರೆಗೆ ಭೇಟಿ ನೀಡಿ.`;
    messageTa = `${overdueDays} நாள் தாமதம் (தேதி ${item.due_date}). தாய்-சேய் அட்டையுடன் ஆரம்ப சுகாதார நிலையம் செல்லவும்.`;
  } else if (item.status === "DUE_SOON") {
    priority = "MEDIUM";
    titleEn = `Vaccine Due Soon: ${item.vaccine_name} (${item.dose_label})`;
    titleHi = `शीघ्र देय टीकाकरण: ${item.vaccine_name} (${item.dose_label})`;
    titleKn = `ಶೀಘ್ರ ಬಾಕಿ ಲಸಿಕೆ: ${item.vaccine_name} (${item.dose_label})`;
    titleTa = `விரைவில் தடுப்பூசி: ${item.vaccine_name} (${item.dose_label})`;
    messageEn =
      item.reminder_text.trim().length > 0
        ? item.reminder_text
        : item.days_delta === 0
          ? `Due today (${item.due_date}). Visit VHND/PHC with MCP Card.`
          : `Due in ${item.days_delta} day(s) (${item.due_date}). Prepare MCP Card.`;
    messageHi =
      item.days_delta === 0
        ? `अद्य देय (${item.due_date})। मातृ-शिशु सुरक्षा पत्रक सहित प्राथमिक स्वास्थ्य केंद्र पर जाएं।`
        : `${item.days_delta} दिवस में देय (${item.due_date})। टीकाकरण हेतु मातृ-शिशु सुरक्षा पत्रक प्रस्तुत रखें।`;
    messageKn =
      item.days_delta === 0
        ? `ಇಂದು ಬಾಕಿ (${item.due_date}). ತಾಯಿ-ಮಗು ಕಾರ್ಡ್ ತೆಗೆದುಕೊಂಡು ಆಸ್ಪತ್ರೆಗೆ ಭೇಟಿ ನೀಡಿ.`
        : `${item.days_delta} ದಿನಗಳಲ್ಲಿ ಬಾಕಿ (${item.due_date}). ಲಸಿಕೆಗಾಗಿ ತಾಯಿ-ಮಗು ಕಾರ್ಡ್ ಸಿದ್ಧವಾಗಿಡಿ.`;
    messageTa =
      item.days_delta === 0
        ? `இன்று நிலுவை (${item.due_date}). தாய்-சேய் அட்டையுடன் ஆரம்ப சுகாதார நிலையம் செல்லவும்.`
        : `${item.days_delta} நாட்களில் நிலுவை (${item.due_date}). தடுப்பூசிக்கு தாய்-சேய் அட்டையை தயாராக வைக்கவும்.`;
  } else {
    priority = "LOW";
    titleEn = `Upcoming Vaccine: ${item.vaccine_name} (${item.dose_label})`;
    titleHi = `आगामी टीकाकरण: ${item.vaccine_name} (${item.dose_label})`;
    titleKn = `ಮುಂಬರುವ ಲಸಿಕೆ: ${item.vaccine_name} (${item.dose_label})`;
    titleTa = `வரவிருக்கும் தடுப்பூசி: ${item.vaccine_name} (${item.dose_label})`;
    messageEn =
      item.reminder_text.trim().length > 0
        ? item.reminder_text
        : `Scheduled on ${item.due_date} (in ${item.days_delta} day(s)).`;
    messageHi = `निर्धारित तिथि ${item.due_date} (${item.days_delta} दिवस शेष)।`;
    messageKn = `ನಿಗದಿತ ದಿನಾಂಕ ${item.due_date} (${item.days_delta} ದಿನ ಬಾಕಿ).`;
    messageTa = `திட்டமிட்ட தேதி ${item.due_date} (${item.days_delta} நாட்கள் உள்ளன).`;
  }

  return {
    id: `vax:${item.vaccine_code}:${item.dose_label}`,
    category: "VACCINATION",
    priority,
    status: item.status,
    dueBy: item.due_date,
    daysDelta: item.days_delta,
    titleEn,
    titleHi,
    titleKn,
    titleTa,
    messageEn,
    messageHi,
    messageKn,
    messageTa,
    title: pickLocalized(language, titleEn, titleHi, titleKn, titleTa),
    message: pickLocalized(language, messageEn, messageHi, messageKn, messageTa),
    sourceCardId: null,
    vaccineCode: item.vaccine_code,
  };
}

function formatActionCardReminder(
  card: ActionCard,
  language: "en" | "hi" | "kn" | "ta",
  includeAcknowledged: boolean,
): WatchReminderItem | null {
  if (card.watch_mode !== null && card.watch_mode !== "PATIENT_FAMILY") {
    return null;
  }
  if (card.status === "COMPLETED" || card.status === "DISMISSED") {
    return null;
  }
  if (card.status === "ACKNOWLEDGED" && !includeAcknowledged) {
    return null;
  }

  const isMedication = isMedicationActionCard(card);
  const category: WatchReminderCategory = isMedication ? "MEDICATION" : "CARE";

  const titleEn = card.title;
  const messageEn = card.summary;

  let titleHi: string;
  let messageHi: string;
  let titleKn: string;
  let messageKn: string;
  let titleTa: string;
  let messageTa: string;

  if (card.language === "hi") {
    titleHi = card.title;
    messageHi = card.summary;
  } else if (isMedication) {
    titleHi =
      card.priority === "CRITICAL"
        ? "आपातकालीन औषधि निर्देश"
        : card.priority === "HIGH"
          ? "अति आवश्यक औषधि अनुस्मारक"
          : "औषधि सेवन अनुस्मारक";
    messageHi = card.due_by
      ? `निर्धारित तिथि ${card.due_by} तक नियमित औषधि सेवन एवं स्वास्थ्य कार्यकर्ता निर्देशों का पालन करें।`
      : "नियमित औषधि सेवन एवं स्वास्थ्य कार्यकर्ता निर्देशों का पालन करें।";
  } else {
    titleHi =
      card.priority === "CRITICAL"
        ? "गंभीर आपातकाल: तत्काल चिकित्सालय संदर्भ"
        : "गृह परिचर्या अनुस्मारक";
    messageHi =
      card.priority === "CRITICAL"
        ? "रोगी वाहन 108 पर तत्काल संपर्क करें एवं निकटतम चिकित्सालय ले जाएं।"
        : "स्वास्थ्य कार्यकर्ता द्वारा निर्दिष्ट गृह परिचर्या एवं परीक्षण का पालन करें।";
  }

  if (card.language === "kn") {
    titleKn = card.title;
    messageKn = card.summary;
  } else if (isMedication) {
    titleKn =
      card.priority === "CRITICAL"
        ? "ತುರ್ತು ಔಷಧ ಸೂಚನೆ"
        : card.priority === "HIGH"
          ? "ಅಗತ್ಯ ಔಷಧ ನೆನಪು"
          : "ಔಷಧ ಸೇವನೆ ನೆನಪು";
    messageKn = card.due_by
      ? `${card.due_by} ಒಳಗೆ ನಿಯಮಿತವಾಗಿ ಔಷಧ ತೆಗೆದುಕೊಳ್ಳಿ ಮತ್ತು ಆಶಾ ಕಾರ್ಯಕರ್ತೆಯ ಸೂಚನೆ ಪಾಲಿಸಿ.`
      : "ನಿಯಮಿತವಾಗಿ ಔಷಧ ತೆಗೆದುಕೊಳ್ಳಿ ಮತ್ತು ಆಶಾ ಕಾರ್ಯಕರ್ತೆಯ ಸೂಚನೆ ಪಾಲಿಸಿ.";
  } else {
    titleKn =
      card.priority === "CRITICAL"
        ? "ಕೆಂಪು ತುರ್ತು: ತಕ್ಷಣ ಆಸ್ಪತ್ರೆಗೆ ಕರೆದೊಯ್ಯಿರಿ"
        : "ಮನೆ ಆರೈಕೆ ನೆನಪು";
    messageKn =
      card.priority === "CRITICAL"
        ? "ತಕ್ಷಣ 108 ಕರೆ ಮಾಡಿ ಮತ್ತು ಹತ್ತಿರದ ಆಸ್ಪತ್ರೆಗೆ ಕರೆದೊಯ್ಯಿರಿ."
        : "ಆಶಾ ಕಾರ್ಯಕರ್ತೆ ತಿಳಿಸಿದ ಮನೆ ಆರೈಕೆ ಮತ್ತು ತಪಾಸಣೆ ಪಾಲಿಸಿ.";
  }

  if (card.language === "ta") {
    titleTa = card.title;
    messageTa = card.summary;
  } else if (isMedication) {
    titleTa =
      card.priority === "CRITICAL"
        ? "அவசர மருந்து அறிவுறுத்தல்"
        : card.priority === "HIGH"
          ? "முக்கிய மருந்து நினைவூட்டல்"
          : "மருந்து உட்கொள்ளல் நினைவூட்டல்";
    messageTa = card.due_by
      ? `${card.due_by} க்குள் தவறாமல் மருந்து உட்கொண்டு ஆஷா பணியாளர் அறிவுறுத்தலைப் பின்பற்றவும்.`
      : "தவறாமல் மருந்து உட்கொண்டு ஆஷா பணியாளர் அறிவுறுத்தலைப் பின்பற்றவும்.";
  } else {
    titleTa =
      card.priority === "CRITICAL"
        ? "சிவப்பு அவசரம்: உடனடி மருத்துவமனை"
        : "வீட்டு பராமரிப்பு நினைவூட்டல்";
    messageTa =
      card.priority === "CRITICAL"
        ? "உடனடியாக 108 அழைத்து அருகிலுள்ள மருத்துவமனைக்கு அழைத்துச் செல்லவும்."
        : "ஆஷா பணியாளர் தெரிவித்த வீட்டு பராமரிப்பு மற்றும் பரிசோதனையைப் பின்பற்றவும்.";
  }

  return {
    id: `card:${card.card_id}`,
    category,
    priority: card.priority,
    status: card.status,
    dueBy: card.due_by,
    daysDelta: null,
    titleEn,
    titleHi,
    titleKn,
    titleTa,
    messageEn,
    messageHi,
    messageKn,
    messageTa,
    title: pickLocalized(language, titleEn, titleHi, titleKn, titleTa),
    message: pickLocalized(language, messageEn, messageHi, messageKn, messageTa),
    sourceCardId: card.card_id,
    vaccineCode: null,
  };
}

function compareReminders(a: WatchReminderItem, b: WatchReminderItem): number {
  const rankDiff = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
  if (rankDiff !== 0) {
    return rankDiff;
  }

  if (a.dueBy !== b.dueBy) {
    if (a.dueBy === null) return 1;
    if (b.dueBy === null) return -1;
    const dateDiff = a.dueBy.localeCompare(b.dueBy);
    if (dateDiff !== 0) return dateDiff;
  }

  const deltaA = a.daysDelta ?? Number.MAX_SAFE_INTEGER;
  const deltaB = b.daysDelta ?? Number.MAX_SAFE_INTEGER;
  if (deltaA !== deltaB) {
    return deltaA - deltaB;
  }

  return a.id.localeCompare(b.id);
}

/**
 * Projects synced `VaccinationDueItem` records and `PATIENT_FAMILY` `ActionCard`s
 * into compact, priority-sorted watch reminders.
 *
 * Mapping:
 * - `OVERDUE` vaccination -> `HIGH`
 * - `DUE_SOON` vaccination -> `MEDIUM`
 * - `COMPLETED` vaccination / `COMPLETED` or `DISMISSED` ActionCard -> hidden
 */
export function projectPatientFamilyReminders(
  input: ReminderProjectionInput,
): WatchReminderItem[] {
  const language: "en" | "hi" | "kn" | "ta" =
    input.language === "hi"
      ? "hi"
      : input.language === "kn"
        ? "kn"
        : input.language === "ta"
          ? "ta"
          : "en";
  const includeUpcoming = input.includeUpcoming ?? false;
  const includeAcknowledged = input.includeAcknowledged ?? false;

  const items: WatchReminderItem[] = [];

  for (const vax of input.vaccinations ?? []) {
    const projected = formatVaccinationReminder(vax, language, includeUpcoming);
    if (projected !== null) {
      items.push(projected);
    }
  }

  for (const card of input.actionCards ?? []) {
    const projected = formatActionCardReminder(card, language, includeAcknowledged);
    if (projected !== null) {
      items.push(projected);
    }
  }

  items.sort(compareReminders);
  return items;
}
