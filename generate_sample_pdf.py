import pymupdf  # PyMuPDF

doc = pymupdf.open()

# --- Page 1: Computer Networks ---
p1 = doc.new_page()
p1.insert_text((50, 60), """CHAPTER 1: COMPUTER NETWORKING & THE OSI MODEL

1.1 What is a Computer Network?
A computer network is a collection of interconnected devices that exchange data and share resources using common communication protocols over physical or wireless links.

1.2 The 7-Layer OSI Reference Model
The Open Systems Interconnection (OSI) framework partitions network operations into seven layers:
1. Physical Layer: Transmits raw unstructured bit streams across physical mediums (cables, fiber optics, radio frequencies).
2. Data Link Layer: Manages node-to-node frame transfer and error detection across local physical links (e.g., Ethernet, MAC addresses).
3. Network Layer: Handles logical addressing and determines the optimal path for packets across multiple networks (e.g., Internet Protocol or IP).
4. Transport Layer: Guarantees end-to-end communication reliability, segmentation, and flow control (e.g., TCP for reliable delivery, UDP for low-latency streaming).
5. Session Layer: Establishes, manages, and terminates conversational sessions between remote hosts.
6. Presentation Layer: Performs data formatting, syntax translation, encryption, and compression (e.g., TLS/SSL, JSON, JPEG).
7. Application Layer: Provides network services directly to end-user software applications (e.g., HTTP, DNS, SMTP, SSH).
""", fontsize=11)

# --- Page 2: Operating Systems ---
p2 = doc.new_page()
p2.insert_text((50, 60), """CHAPTER 2: OPERATING SYSTEMS & PROCESS MANAGEMENT

2.1 Role of an Operating System
An Operating System (OS) is core system software that supervises hardware components, allocates system memory, manages file systems, and acts as an intermediary between user software and hardware.

2.2 Processes vs. Threads
- Process: An executing program instance with its own dedicated memory address space, file handles, and security context. Processes are isolated from one another.
- Thread: The smallest unit of CPU execution within a process, often termed a lightweight process. Multiple threads within the same process share code, global memory, and open resources, but each thread retains its own program counter and stack.

2.3 CPU Scheduling and Concurrency Deadlocks
The CPU scheduler selects which ready process executes on the CPU core using algorithms like Round Robin (time slicing), First-Come First-Served, or Priority Scheduling.
A Deadlock is an execution stall where two or more processes are permanently blocked because each holds a resource that the other process requires to proceed.
""", fontsize=11)

# --- Page 3: Cloud Computing ---
p3 = doc.new_page()
p3.insert_text((50, 60), """CHAPTER 3: CLOUD COMPUTING & VIRTUALIZATION

3.1 Core Principles of Cloud Computing
Cloud computing provides on-demand network access to a shared pool of configurable computing resources (servers, storage, databases, networking, and software) with minimal management effort and pay-as-you-go pricing.

3.2 Cloud Service Models (SPI Model)
1. Infrastructure as a Service (IaaS): Delivers fundamental virtualized compute instances, raw storage, and software-defined networking. The consumer manages operating systems, runtimes, and applications (e.g., AWS EC2, Google Compute Engine).
2. Platform as a Service (PaaS): Delivers managed hardware and operating environments where developers deploy application code without managing underlying servers or OS patching (e.g., AWS Elastic Beanstalk, Heroku).
3. Software as a Service (SaaS): Delivers fully managed, ready-to-use software applications accessible through a browser or API (e.g., Google Workspace, Salesforce, Microsoft 365).

3.3 Virtual Machines vs. Containers
- Virtual Machines (VMs): Use a hypervisor to emulate complete physical hardware, running a full guest operating system on each VM.
- Containers: Virtualize at the operating system level, sharing the host OS kernel to package application code and dependencies into fast, lightweight instances (e.g., Docker).
""", fontsize=11)

output_filename = "Computer_Science_Fundamentals.pdf"
doc.save(output_filename)
doc.close()
print(f"Generated {output_filename} successfully!")
