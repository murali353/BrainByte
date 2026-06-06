// Firebase Imports
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";

import {
    getAuth,
    createUserWithEmailAndPassword,
    signInWithEmailAndPassword,
    GoogleAuthProvider,
    signInWithPopup
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

// FIRESTORE
import {
    getFirestore
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

// FIREBASE CONFIG
const firebaseConfig = {

    apiKey: "AIzaSyAIArJLQsT7ULj0hnfO_B0poQO7ZZrmZug",

    authDomain: "brain-byte-dd2a8.firebaseapp.com",

    projectId: "brain-byte-dd2a8",

    storageBucket: "brain-byte-dd2a8.appspot.com",

    messagingSenderId: "715587394567",

    appId: "1:715587394567:web:9aecaea8fafaf1b369dea2"
};

// INITIALIZE FIREBASE
const app = initializeApp(firebaseConfig);

const auth = getAuth(app);

const db = getFirestore(app);

const provider = new GoogleAuthProvider();

// EXPORTS
export {

    auth,

    db,

    provider,

    createUserWithEmailAndPassword,

    signInWithEmailAndPassword,

    signInWithPopup
};