import type { Lang } from "./brand";

export interface Metric { num: string; label: string; note: string; }
export interface FeatureItem { tag: string; title: string; body: string; }
export interface IntegrationStep { n: string; title: string; body: string; }
export interface Quote { text: string; name: string; role: string; }
export interface PricingTier { name: string; price: string; per: string; desc: string; feats: string[]; highlight?: boolean; }
export interface FaqItem { q: string; a: string; }

export interface CopyShape {
  nav: { product: string; pricing: string; cases: string; docs: string; login: string; cta: string; };
  hero: { eyebrow: string; headline_a: string; headline_b: string; sub: string; cta_primary: string; cta_secondary: string; trust: string; };
  metrics: Metric[];
  features: { eyebrow: string; title: string; sub: string; items: FeatureItem[]; };
  integration: { eyebrow: string; title: string; steps: IntegrationStep[]; };
  proof: { eyebrow: string; title: string; quotes: Quote[]; };
  pricing: { eyebrow: string; title: string; sub: string; tiers: PricingTier[]; revshare: string; };
  faq: { eyebrow: string; items: FaqItem[]; };
  final_cta: { title: string; sub: string; cta: string; };
  footer: { tag: string; cols: { product: string[]; company: string[]; legal: string[]; }; };
}

const de: CopyShape = {
  nav: { product: "Produkt", pricing: "Preise", cases: "Cases", docs: "Docs", login: "Login", cta: "Demo buchen" },
  hero: {
    eyebrow: "KI-Kaufberater für WooCommerce",
    headline_a: "Beratung, die\nverkauft. Rund\num die Uhr.",
    headline_b: "Jeder Besucher\nverdient einen\nFachverkäufer.",
    sub: "__NAME__ ist der KI-Berater, der Ihre Kunden im Shop führt — fragt nach, schlägt das Richtige vor, beantwortet Detailfragen. Wie Ihr bester Mitarbeiter, nur 24/7 und in jeder Sprache.",
    cta_primary: "14 Tage kostenlos testen",
    cta_secondary: "Live-Demo ansehen",
    trust: "Keine Kreditkarte · DSGVO-konform · In 8 Minuten installiert",
  },
  metrics: [
    { num: "+27%", label: "Conversion-Rate", note: "Median über 240 Shops" },
    { num: "−18%", label: "Retourenquote", note: "passendere Käufe" },
    { num: "+34€", label: "Warenkorbwert", note: "Cross-Sell on Demand" },
    { num: "24/7", label: "Verfügbar", note: "in 32 Sprachen" },
  ],
  features: {
    eyebrow: "So funktioniert's",
    title: "Ein Verkäufer, der\nIhren Katalog kennt.",
    sub: "__NAME__ liest Ihren WooCommerce-Katalog inkl. Attributen, Bewertungen und Lagerbestand — und führt Gespräche, die zum Produkt passen.",
    items: [
      { tag: "01", title: "Versteht Bedarf", body: "Stellt die Fragen, die ein Verkäufer auf der Fläche stellen würde — und lernt aus jedem Gespräch." },
      { tag: "02", title: "Empfiehlt passgenau", body: "Vergleicht Produkte aus Ihrem Sortiment, erklärt Unterschiede, weist auf Alternativen hin." },
      { tag: "03", title: "Schließt ab", body: "Legt Artikel direkt in den Warenkorb, bietet Rabatte gezielt an und übergibt sauber an den Checkout." },
      { tag: "04", title: "Lernt mit", body: "Sie sehen jedes Gespräch, jede Conversion, jede offene Frage — und können Antworten in einem Klick verbessern." },
    ],
  },
  integration: {
    eyebrow: "Integration",
    title: "Plugin installieren.\nFertig.",
    steps: [
      { n: "1", title: "WooCommerce-Plugin aktivieren", body: "Standard-Installation aus dem WordPress-Backend. Keine Code-Änderungen nötig." },
      { n: "2", title: "Katalog wird automatisch indiziert", body: "Produkte, Varianten, Kategorien, Bewertungen — direkt aus Ihrer WooCommerce-Datenbank." },
      { n: "3", title: "Tonalität & Regeln festlegen", body: "Wie spricht Ihre Marke? Was darf der Berater (nicht) tun? In 5 Minuten konfiguriert." },
      { n: "4", title: "Live schalten", body: "Als Chat-Widget, im Produktdetail oder als kompletter Beratungs-Assistent. Sie entscheiden." },
    ],
  },
  proof: {
    eyebrow: "Stimmen aus dem Handel",
    title: "Was Shop-Betreiber\nsagen.",
    quotes: [
      { text: "Wir hatten Bedenken, dass ein KI-Bot unsere Marke verwässert. Nach zwei Wochen war klar: Die Beratung ist besser als unser eigenes Team in der Hochsaison.", name: "[Kundenname]", role: "Geschäftsführerin · [Brand]" },
      { text: "Conversion-Rate ist nicht alles — aber wenn der durchschnittliche Warenkorb gleichzeitig steigt und die Retourenquote sinkt, dann ist das ein No-Brainer.", name: "[Kundenname]", role: "Head of E-Commerce · [Brand]" },
    ],
  },
  pricing: {
    eyebrow: "Preise",
    title: "Bezahlen Sie nach\nErgebnis. Nicht nach\nGespräch.",
    sub: "Eine monatliche Basis. Eine kleine Provision auf Käufe, die durch __NAME__ entstehen. Sonst nichts.",
    tiers: [
      { name: "Starter", price: "49 €", per: "/ Monat", desc: "Für Shops bis 5.000 Sessions/Monat", feats: ["1 KI-Berater", "WooCommerce-Integration", "DE & EN", "E-Mail Support"] },
      { name: "Growth", price: "149 €", per: "/ Monat", desc: "Für wachsende Shops", feats: ["Unbegrenzt Sessions", "Eigene Markenstimme", "32 Sprachen", "Cross-Sell-Logik", "Prio Support"], highlight: true },
      { name: "Scale", price: "Auf Anfrage", per: "", desc: "Mehrere Shops, Enterprise", feats: ["SLA & DPA", "Dedicated CSM", "Eigene Modelle", "API-Zugang"] },
    ],
    revshare: "+ 1,5% auf direkt zugeordneten Umsatz · keine Setup-Gebühr · monatlich kündbar",
  },
  faq: {
    eyebrow: "Häufige Fragen",
    items: [
      { q: "Wie lange dauert die Einrichtung?", a: "Plugin in 8 Minuten installiert. Kataloglesung läuft automatisch im Hintergrund. Erste Konfiguration der Tonalität in 30 Minuten machbar." },
      { q: "Was kostet mich das pro Gespräch?", a: "Nichts. Sie zahlen eine Monatslizenz und 1,5% auf Käufe, die durch den Berater entstehen — sonst nichts." },
      { q: "Was passiert bei Datenschutz?", a: "DSGVO-konform, Server in der EU, kein Tracking ohne Einwilligung. AVV stellen wir bereit." },
      { q: "Kann ich den Berater an meine Marke anpassen?", a: "Ja — Stimme, Erlaubnisse, Ausnahmen, Begrüßung, Farbe. Alles über das Backend." },
      { q: "Was, wenn der Berater eine falsche Antwort gibt?", a: "Sie sehen jedes Gespräch und können Antworten mit einem Klick korrigieren — der Berater lernt sofort." },
    ],
  },
  final_cta: {
    title: "Sehen Sie es\nin Ihrem Shop.",
    sub: "30-Minuten-Demo mit Ihren echten Produkten. Keine Folien, kein Sales-Pitch.",
    cta: "Demo-Termin wählen",
  },
  footer: {
    tag: "Made for WooCommerce. Built in EU.",
    cols: {
      product: ["Features", "Preise", "Integrationen", "Roadmap"],
      company: ["Über uns", "Kunden", "Blog", "Kontakt"],
      legal: ["Datenschutz", "AGB", "AVV", "Impressum"],
    },
  },
};

const en: CopyShape = {
  nav: { product: "Product", pricing: "Pricing", cases: "Cases", docs: "Docs", login: "Login", cta: "Book a demo" },
  hero: {
    eyebrow: "AI shopping advisor for WooCommerce",
    headline_a: "Advice that\nsells. Around\nthe clock.",
    headline_b: "Every visitor\ndeserves an\nexpert.",
    sub: "__NAME__ is the AI advisor that guides your customers in-store — asks questions, suggests the right thing, answers detail queries. Like your best rep, but 24/7 and in any language.",
    cta_primary: "Try free for 14 days",
    cta_secondary: "See live demo",
    trust: "No credit card · GDPR-ready · Live in 8 minutes",
  },
  metrics: [
    { num: "+27%", label: "Conversion rate", note: "Median across 240 shops" },
    { num: "−18%", label: "Return rate", note: "better-fit purchases" },
    { num: "+€34", label: "Cart value", note: "cross-sell on demand" },
    { num: "24/7", label: "Available", note: "in 32 languages" },
  ],
  features: {
    eyebrow: "How it works",
    title: "A salesperson\nwho knows your\ncatalog.",
    sub: "__NAME__ reads your WooCommerce catalog incl. attributes, reviews and stock — and runs conversations that fit the product.",
    items: [
      { tag: "01", title: "Understands need", body: "Asks what a shop-floor expert would ask — and learns from every conversation." },
      { tag: "02", title: "Recommends the right thing", body: "Compares products from your range, explains differences, points out alternatives." },
      { tag: "03", title: "Closes", body: "Adds items to cart, offers targeted discounts, hands off cleanly to checkout." },
      { tag: "04", title: "Improves itself", body: "See every conversation, every conversion, every open question — fix answers in one click." },
    ],
  },
  integration: {
    eyebrow: "Integration",
    title: "Install the plugin.\nDone.",
    steps: [
      { n: "1", title: "Activate WooCommerce plugin", body: "Standard install from the WordPress backend. No code changes." },
      { n: "2", title: "Catalog auto-indexed", body: "Products, variants, categories, reviews — straight from your WooCommerce database." },
      { n: "3", title: "Set tone & rules", body: "How does your brand speak? What can the advisor (not) do? Configured in 5 minutes." },
      { n: "4", title: "Go live", body: "As a chat widget, on PDPs, or a full advisor flow. Your call." },
    ],
  },
  proof: {
    eyebrow: "From the field",
    title: "What shop\nowners say.",
    quotes: [
      { text: "We worried an AI bot would water down our brand. Two weeks in, the advice was sharper than our own team in peak season.", name: "[Customer]", role: "CEO · [Brand]" },
      { text: "Conversion rate isn't everything — but when AOV goes up and returns go down at the same time, it's a no-brainer.", name: "[Customer]", role: "Head of E-commerce · [Brand]" },
    ],
  },
  pricing: {
    eyebrow: "Pricing",
    title: "Pay for outcomes,\nnot conversations.",
    sub: "A small monthly base. A small share on revenue we drive. That's it.",
    tiers: [
      { name: "Starter", price: "€49", per: "/mo", desc: "For shops up to 5k sessions/mo", feats: ["1 AI advisor", "WooCommerce integration", "DE & EN", "Email support"] },
      { name: "Growth", price: "€149", per: "/mo", desc: "For growing shops", feats: ["Unlimited sessions", "Custom brand voice", "32 languages", "Cross-sell logic", "Priority support"], highlight: true },
      { name: "Scale", price: "On request", per: "", desc: "Multi-shop, enterprise", feats: ["SLA & DPA", "Dedicated CSM", "Custom models", "API access"] },
    ],
    revshare: "+ 1.5% on directly attributed revenue · no setup fee · monthly cancellation",
  },
  faq: {
    eyebrow: "Common questions",
    items: [
      { q: "How long does setup take?", a: "Plugin installed in 8 minutes. Catalog reading runs in the background. First tone config doable in 30 minutes." },
      { q: "What does each conversation cost me?", a: "Nothing. You pay a monthly license + 1.5% on advisor-driven purchases — that's it." },
      { q: "Data protection?", a: "GDPR-compliant, EU servers, no tracking without consent. DPA available." },
      { q: "Can I match it to my brand?", a: "Yes — voice, permissions, exceptions, greeting, color. All from the backend." },
      { q: "What if the advisor gives a wrong answer?", a: "You see every conversation and can fix answers in one click — the advisor learns immediately." },
    ],
  },
  final_cta: { title: "See it in\nyour shop.", sub: "30-minute demo with your real products. No slides, no sales pitch.", cta: "Pick a demo slot" },
  footer: {
    tag: "Made for WooCommerce. Built in EU.",
    cols: {
      product: ["Features", "Pricing", "Integrations", "Roadmap"],
      company: ["About", "Customers", "Blog", "Contact"],
      legal: ["Privacy", "Terms", "DPA", "Imprint"],
    },
  },
};

export const COPY: Record<Lang, CopyShape> = { de, en };
