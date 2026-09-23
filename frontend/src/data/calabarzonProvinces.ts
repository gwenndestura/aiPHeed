export const PROVINCE_LIST = ["Quezon", "Batangas", "Rizal", "Cavite", "Laguna"] as const;
export type ProvinceName = typeof PROVINCE_LIST[number];

export const MUNICIPALITIES_BY_PROVINCE: Record<ProvinceName, string[]> = {
  Quezon: [
    "Lucena City", "Tayabas City", "Atimonan", "Buenavista", "Burdeos", "Calauag", "Candelaria",
    "Catanauan", "General Luna", "Guinayangan", "Gumaca", "Infanta", "Lopez", "Lucban", "Macalelon",
    "Mulanay", "Padre Burgos", "Pagbilao", "Panukulan", "Perez", "Pitogo", "Plaridel", "Polillo",
    "Quezon", "Real", "Sampaloc", "San Andres", "San Antonio", "San Francisco", "San Narciso",
    "Sariaya", "Tagkawayan", "Tiaong", "Unisan", "Alabat",
  ],
  Batangas: [
    "Batangas City", "Lipa City", "Tanauan City", "Alaminos", "Alitagtag", "Balayan", "Balete",
    "Bauan", "Calaca", "Calatagan", "Cuenca", "Ibaan", "Laurel", "Lemery", "Lian", "Lobo",
    "Mabini", "Malvar", "Mataas na Kahoy", "Nasugbu", "Padre Garcia", "Rosario", "San Jose",
    "San Juan", "San Luis", "San Nicolas", "San Pascual", "Santa Teresita", "Santo Tomas",
    "Taal", "Taysan", "Tingloy", "Tuy",
  ],
  Rizal: [
    "Antipolo City", "Angono", "Baras", "Binangonan", "Cainta", "Cardona", "Jala-Jala", "Morong",
    "Pililla", "Rodriguez", "San Mateo", "Tanay", "Taytay", "Teresa",
  ],
  Cavite: [
    "Cavite City", "Bacoor", "Dasmariñas", "General Trias", "Imus", "Tagaytay", "Trece Martires",
    "Alfonso", "Amadeo", "Carmona", "General Mariano Alvarez", "Indang", "Kawit", "Magallanes",
    "Maragondon", "Mendez", "Naic", "Noveleta", "Rosario", "Silang", "Tanza", "Ternate",
  ],
  Laguna: [
    "Calamba", "San Pablo", "Santa Rosa", "Biñan", "Cabuyao", "San Pedro", "Alaminos", "Bay",
    "Calauan", "Cavinti", "Famy", "Kalayaan", "Liliw", "Los Baños", "Luisiana", "Lumban",
    "Mabitac", "Magdalena", "Majayjay", "Nagcarlan", "Paete", "Pagsanjan", "Pakil", "Pangil",
    "Pila", "Rizal", "Santa Cruz", "Santa Maria", "Siniloan", "Victoria",
  ],
};
