import type { Lang } from "../../data/brand";

export type EmailVariant = "direct" | "story" | "followup";

export interface EmailTemplate {
  label: string;
  subject: string;
  body: string[];
}

interface BuildArgs {
  lang: Lang;
  name: string;
}

export function buildEmail(variant: EmailVariant, { lang, name }: BuildArgs): EmailTemplate {
  const isDe = lang === "de";
  if (isDe) {
    if (variant === "direct") {
      return {
        label: "Direkt · ROI-fokussiert",
        subject: `[Shop-Name]: +27% Conversion mit KI-Beratung`,
        body: [
          "Hi [Vorname],",
          "",
          `kurz und ehrlich: Wir haben für 240 WooCommerce-Shops einen KI-Berater gebaut, der die Conversion-Rate im Median um 27% erhöht und gleichzeitig die Retourenquote senkt.`,
          "",
          `Bei [Shop-Name] sehe ich [konkrete Beobachtung — z.B. „eine breite Auswahl an [Kategorie] ohne Beratungsangebot"]. Genau da setzt __NAME__ an.`,
          "",
          "Hätten Sie 20 Minuten in den nächsten 2 Wochen, damit ich Ihnen den Berater LIVE mit Ihren echten Produkten zeige?",
          "",
          "Beste Grüße,",
          "[Ihr Name]",
        ],
      };
    }
    if (variant === "story") {
      return {
        label: "Story · Mit Beobachtung",
        subject: `Beobachtung zu Ihrem Shop`,
        body: [
          "Hallo [Vorname],",
          "",
          "ich war gerade in [Shop-Name]. Schöner Auftritt — aber als ich nach [konkrete Suche] gesucht habe, kamen 47 Produkte ohne Hilfe, welches für meinen Anwendungsfall passt.",
          "",
          `Genau das ist der Moment, in dem __NAME__ im Laden die Verkäuferin wäre, die fragt: „Wofür brauchen Sie es?" — und dann 2 sinnvolle Optionen rauspickt.`,
          "",
          "Wir bauen das als WooCommerce-Plugin. Installation in 8 Minuten, im Median +27% Conversion in den ersten 90 Tagen.",
          "",
          "Wäre eine 20-Minuten-Demo mit Ihren echten Produkten interessant?",
          "",
          "Viele Grüße,",
          "[Ihr Name]",
        ],
      };
    }
    return {
      label: "Follow-up · kurz",
      subject: `Re: __NAME__ für [Shop-Name]`.replace(/__NAME__/g, name),
      body: [
        "Hi [Vorname],",
        "",
        "ich nehme an, meine letzte Mail ist im Trubel untergegangen.",
        "",
        "Eine Zahl, die vielleicht relevant ist: 97% Ihrer Besucher kaufen nichts. Die meisten nicht, weil sie nicht wollen — sondern weil sie nicht das Richtige finden.",
        "",
        `__NAME__ schließt diese Lücke. 14 Tage kostenlos, kündbar in einem Klick.`,
        "",
        "Soll ich einen 20-Min-Slot vorschlagen?",
        "",
        "Beste Grüße,",
        "[Ihr Name]",
      ],
    };
  }

  // EN
  if (variant === "direct") {
    return {
      label: "Direct · ROI-focused",
      subject: `[Shop name]: +27% conversion with AI advising`,
      body: [
        "Hi [First name],",
        "",
        `Short and honest: we've built an AI advisor for 240 WooCommerce shops that lifts conversion by a median 27% and cuts returns at the same time.`,
        "",
        `Looking at [Shop name], I see [concrete observation — e.g. "a broad [category] range with no guidance"]. That's exactly where __NAME__ fits.`,
        "",
        "Could you spare 20 minutes in the next two weeks so I can show you the advisor LIVE with your real products?",
        "",
        "Best,",
        "[Your name]",
      ],
    };
  }
  if (variant === "story") {
    return {
      label: "Story · with observation",
      subject: "An observation about your shop",
      body: [
        "Hi [First name],",
        "",
        "I just visited [Shop name]. Nice site — but when I searched for [concrete search], 47 products came up with zero help on which fits my use case.",
        "",
        `That's the moment where, in-store, __NAME__ would be the salesperson asking "what do you need it for?" and then narrowing it to 2 sensible options.`,
        "",
        "We build that as a WooCommerce plugin. 8-minute install, median +27% conversion in the first 90 days.",
        "",
        "Worth a 20-minute demo with your real products?",
        "",
        "Cheers,",
        "[Your name]",
      ],
    };
  }
  return {
    label: "Follow-up · short",
    subject: `Re: __NAME__ for [Shop name]`.replace(/__NAME__/g, name),
    body: [
      "Hi [First name],",
      "",
      "Guessing my last note got buried.",
      "",
      "One number that might matter: 97% of your visitors don't buy. Most not because they don't want to — they just don't find the right thing.",
      "",
      `__NAME__ closes that gap. 14 days free, cancel in one click.`,
      "",
      "Want me to propose a 20-min slot?",
      "",
      "Best,",
      "[Your name]",
    ],
  };
}
