var slider = document.getElementById("slider");
var output = document.getElementById("value");

output.innerHTML = slider.value;

slider.oninput = function() {
    output.innerHTML = this.value;
}

slider.addEventListener("mousemove",function(){
    var x = this.value;
    var color = 'linear-gradient(90deg,rgb(117,252,117)'+ x + '%, #FFFFFF' + x + '%)';
    slider.style.background=color
})