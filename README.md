# CS242P - Building a LL(1) SMPL Recursive Descent Parser

Class project directed by [Michael Franz](https://www.michaelfranz.com/home) where students spend 10 weeks independently creating a SMPL parser. 
The project was a solo project created entirely from scratch in Python, using only one external library (PyDot) which is used for converting the CFG into dot for visualization. 
## Features
- **Single Static Assignment (SSA)** – Converts intermediate representation into SSA form for easier optimization.
- **Common Subexpression Elimination (CSE)** – Eliminates redundant expressions to optimize computation.
- **Dominance Frontier** – Used to compute precise placement of φ (phi) functions for SSA conversion.
- **Phi Functions & Reducible Control Flow** – Handles variables with multiple definitions across branches and ensures well-structured control flow graphs.

## Usage
```bash
python main.py source_file.smpl
```

## Example Input (SMPL)
```
main
var a,b,c,d,e;
{
    let a<-call InputNum(); 
    let b<-a; 
    let c<-b; 
    let d<- b+ c; 
    let e <-a+b;
    if a<0 then 
        let d<-d+e; 
        let a<- d 
    else 
        let d<- e  
    fi;
    call OutputNum(a)
}.
```
## Output
![CFG Output](https://github.com/b1wang/LL1-Compiler/blob/main/test_cases/simple_if_output.png)

## Dependencies
- Python 3.8+
- PyDot

## Credits
Developed as part of UC Irvine’s CS242P Compiler Construction course.
Supervised by Prof. Michael Franz.
