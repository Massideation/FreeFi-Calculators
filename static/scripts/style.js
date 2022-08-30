var slider = document.getElementById("slider");
var output = document.getElementById("value");

output.innerHTML = slider.value;

slider.oninput = function() {
    output.innerHTML = this.value;
}

slider.addEventListener("mousemove",function(){
    var x = (this.value-20)*100/(80-20);
    var color = 'linear-gradient(90deg, lightgreen '+ x + '%, white ' + x + '%)';
    slider.style.background=color
})

let nums = document.querySelectorAll("#money");
for (let i = 0, len = nums. length; i < len; i++) {
    let num = Number(nums[i].innerHTML).toLocaleString('en',{ style: 'currency', currency: 'USD'});
    nums[i].innerHTML = num;
}