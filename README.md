L'applicazione simulazione.py necessita dei pacchetti satkit e pyvista per funzionare.

simulazione.py cerca i satelliti che soddisfano alcune condizioni all'interno di satelliti.db,
ad esempio cercando i satelliti che sono 10° sopra l'orizzonte rispetto a un punto sulla superficie terrestre in un determinato intervallo di tempo a scelta,
per poi visualizzare il movimento e le traiettorie dei satelliti scelti.

Alcune selezioni possono non trovare satelliti e fanno fallire la simulazione

All'interno della visualizzazione è possibile cliccare sui satelliti e ottenere informazioni su di essi, in particolare quando si seleziona un satellite compare
un cerchio sulla superficie della Terra che racchiude l'insieme dei punti per cui il satellite si trova più di 10° sopra l'orizzonte in quell'istante di tempo.

satelliti.db è una versione semplificata in SQLite della base di dati del progetto d'esame, che presenta solo le tabelle e gli attributi necessari per l'applicazione
