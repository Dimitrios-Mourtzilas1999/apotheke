document.addEventListener('DOMContentLoaded',()=>{
    const productID = document.querySelector('.product_id');
    console.log(productID);
    productID.addEventListener('keydown',(event)=>{
        console.log(event.target);
    })
})