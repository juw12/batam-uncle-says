/* Batam Uncle Says - local guide booking settings.
   After editing, bump VERSION in sw.js so phones pick up the change. */
window.BUS_PARTNERS = {
  // WhatsApp number that receives tourist requests and guide sign-ups.
  // Digits only, with country code, for example "6281234567890".
  // Empty = the Local guide section stays hidden on the live site (preview with ?guides=1).
  whatsapp: "",

  // Referral fee the guide pays after a completed trip, in percent of their price.
  referral_fee_pct: 10,

  // Published day-charter prices from Batam operators (car, English-speaking driver, fuel, parking).
  charter: {
    checked: "2026-11-07",
    hours: 10,
    mpv_sgd: [55, 80],
    van_sgd: [110, 180],
    sources: [
      "https://batamholiday.com/",
      "https://www.batamprivatetours.com/",
      "https://www.klook.com/en-GB/activity/109324-private-car-charter-batam/"
    ]
  },

  // Batam guide licence rule (Kartu Tanda Pengenal Pramuwisata, Perwako Batam No. 56/2018).
  licence_source: "https://mediacenter.batam.go.id/2019/04/30/hpi-sambut-baik-perwako-pramuwisata/"
};
