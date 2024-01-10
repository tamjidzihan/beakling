const bookList = document.querySelectorAll(".booklist");
const bookListContainer = document.querySelector(".booklist-container");
const nextBtn = document.querySelector(".next-btn");
const pervBtn = document.querySelector(".perv-btn");
const navigationsDots = document.querySelector(".navigation-dots");

let numberOfBooks = bookList.length;
let slideWidth = bookList[0].clientWidth;
let currentSlide = 0

function init() {
    bookList.forEach((img, i) => {
        img.style.left = i * 100 + "%";
    })
    bookList[0].classList.add("active");
    createNavigationDots();
}

init();


function createNavigationDots() {
    for (let i = 0; i < numberOfBooks; i++) {
        const dot = document.createElement("div");
        dot.classList.add("single-dot");
        navigationsDots.appendChild(dot);
        dot.addEventListener("click", () => {
            goToSlide(i)
        })
    }
    navigationsDots.children[0].classList.add("active");
}

nextBtn.addEventListener("click", () => {
    if (currentSlide >= numberOfBooks - 1) {
        goToSlide(0);
        return;
    }
    currentSlide++;
    goToSlide(currentSlide);
})


pervBtn.addEventListener("click", () => {
    if (currentSlide <= 0) {
        goToSlide(numberOfBooks - 1);
        console.log(numberOfBooks)
        return;
    }
    currentSlide--;
    goToSlide(currentSlide);
})



function goToSlide(slideNumber) {
    bookListContainer.style.transform = "translateX(-" + slideWidth * slideNumber + "px)";
    currentSlide = slideNumber
    setActiveClass();
}

function setActiveClass() {
    let currentActive = document.querySelector(".booklist.active");
    currentActive.classList.remove("active");
    bookList[currentSlide].classList.add("active");

    let currentDot = document.querySelector(".single-dot.active");
    currentDot.classList.remove("active");
    navigationsDots.children[currentSlide].classList.add("active");

}


document.addEventListener('DOMContentLoaded', function () {
    const burgerIcon = document.getElementById('burger-icon');
    const navBar = document.getElementById('nav-bar');

    burgerIcon.addEventListener('click', function () {
        navBar.classList.toggle('show');
    });
});
