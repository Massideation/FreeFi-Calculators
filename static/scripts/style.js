
const income =  document.querySelector("#income")
const expense = document.querySelector("#expense")
const expense_percent= document.querySelector('#expense_percent')


var val = Math.round(expense.value*100/income.value);


expense.onchange=function(){
    val = Math.round(this.value*100/income.value);
    expense_percent.innerHTML=val;
}

income.onchange=function(){
    val = Math.round(expense.value*100/this.value);
    expense_percent.innerHTML=val;
}

expense_percent.innerHTML=val;


var slider = document.getElementById("slider");
var output = document.getElementById("value");

slider.value = 55.0
output.innerHTML = slider.value;


slider.oninput = function() {
    output.innerHTML = this.value;
}

slider.addEventListener("mousemove",function(){
    const min = 10
    const max = 80
    var x = (this.value-min)*100/(max-min);
    var color = 'linear-gradient(90deg, lightgreen '+ x + '%, white ' + x + '%)';
    slider.style.background=color
})

let nums = document.querySelectorAll("#money");
for (let i = 0, len = nums. length; i < len; i++) {
    let num = Number(nums[i].innerHTML).toLocaleString('en',{ style: 'currency', currency: 'USD'});
    nums[i].innerHTML = num;
}